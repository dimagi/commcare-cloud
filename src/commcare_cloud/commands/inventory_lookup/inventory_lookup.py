from __future__ import print_function

import subprocess
import sys

from clint.textui import puts
from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.environment.main import get_environment

from ...colors import color_error
from .getinventory import (get_monolith_address, get_server_address,
                           split_host_group)


class Lookup(CommandBase):
    command = 'lookup'
    help = """
    Lookup remote hostname or IP address
    """
    arguments = (
        Argument("server", nargs="?", help="""
            Server name/group: postgresql, proxy, webworkers, ... The server
            name/group may be prefixed with 'username@' to login as a
            specific user and may be terminated with '[<n>]' to choose one of
            multiple servers if there is more than one in the group. For
            example: webworkers[0] will pick the first webworker. May also be
            omitted for environments with only a single server.

            Use '-' for default (django_manage[0])
        """),
    )

    def lookup_server_address(self, args):
        try:
            if not args.server:
                return get_monolith_address(args.env_name)
            return get_server_address(args.env_name, args.server)
        except Exception as e:
            self.parser.error("\n" + e.message)

    def run(self, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print(self.lookup_server_address(args))


class _Ssh(Lookup):

    def run(self, args, ssh_args):
        if args.server == '-':
            args.server = 'django_manage[0]'
        address = self.lookup_server_address(args)
        if ':' in address:
            address, port = address.split(':')
            ssh_args = ['-p', port] + ssh_args
        cmd_parts = [self.command, address] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        return subprocess.call(cmd_parts)


class Ssh(_Ssh):
    command = 'ssh'
    help = """
    Connect to a remote host with ssh.

    This will also automatically add the ssh argument `-A`
    when `<server>` is `control`.

    All trailing arguments are passed directly to `ssh`.
    """

    def run(self, args, ssh_args):

        if 'control' in split_host_group(args.server).group and '-A' not in ssh_args:
            # Always include ssh agent forwarding on control machine
            ssh_args = ['-A'] + ssh_args
        ukhf = "UserKnownHostsFile="
        if not any(a.startswith((ukhf, "-o" + ukhf)) for a in ssh_args):
            environment = get_environment(args.env_name)
            ssh_args = ["-o", ukhf + environment.paths.known_hosts] + ssh_args
        return super(Ssh, self).run(args, ssh_args)


class Mosh(_Ssh):
    command = 'mosh'
    help = """
    Connect to a remote host with mosh.

    This will also automatically switch to using ssh with `-A`
    when `<server>` is `control` (because `mosh` doesn't support `-A`).

    All trailing arguments are passed directly to `mosh`
    (or `ssh` in the edge case described above).
    """

    def run(self, args, ssh_args):
        if args.server == 'control' or '-A' in ssh_args:
            print("! mosh does not support ssh agent forwarding, using ssh instead.",
                  file=sys.stderr)
            Ssh(self.parser).run(args, ssh_args)
        return super(Mosh, self).run(args, ssh_args)


class Tmux(_Ssh):
    command = 'tmux'
    help = """
    Connect to a remote host with ssh and open a tmux session.

    Example:

    Rejoin last open tmux window.

    ```
    commcare-cloud <env> tmux -
    ```
    """
    arguments = _Ssh.arguments + (
        Argument('remote_command', nargs='?', help="""
            Command to run in the tmux.
            If a command specified, then it will always run in a new window.
            If a command is *not* specified, then a it will rejoin the most
            recently visited tmux window; only if there are no currently open
            tmux windows will a new one be opened.
        """),
    )

    def run(self, args, ssh_args):
        environment = get_environment(args.env_name)
        public_vars = environment.public_vars
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        cchq_user = public_vars.get('cchq_user', 'cchq')
        # Name tabs like "droberts (2018-04-13)"
        window_name_expression = '"`whoami` (`date +%Y-%m-%d`)"'
        if args.remote_command:
            # add bash as second command to keep tmux open after command exits
            remote_command = shlex_quote('{} ; bash'.format(args.remote_command))
            ssh_args = [
                '-t',
                r'tmux attach \; new-window -n {window_name} {remote_command} '
                r'|| tmux new -n {window_name} {remote_command}'
                .format(
                    remote_command="sudo -iu {} -- sh -c {}".format(cchq_user, remote_command),
                    window_name=window_name_expression,
                )
            ] + ssh_args
        else:
            ssh_args = [
                '-t',
                'tmux attach || tmux new -n {window_name} sudo -iu {cchq_user} '
                .format(cchq_user=cchq_user, window_name=window_name_expression)
            ]
        return Ssh(self.parser).run(args, ssh_args)


class DjangoManage(CommandBase):
    command = 'django-manage'
    help = """
    Run a django management command.

    `commcare-cloud <env> django-manage ...`
    runs `./manage.py ...` on the first django_manage machine of <env> or
    server you specify.
    Omit <command> to see a full list of possible commands.

    Example:

    To open a django shell in a tmux window using the `2018-04-13_18.16` release.

    ```
    commcare-cloud <env> django-manage --tmux --release 2018-04-13_18.16 shell
    ```
    
    To do this on a specific server

    ```
    commcare-cloud <env> django-manage --tmux shell --server web0
    ```
    """

    arguments = (
        Argument('--tmux', action='store_true', default=False, help="""
            If this option is included, the management command will be
            run in a new tmux window under the `cchq` user. You may then exit using
            the customary tmux command `^b` `d`, and resume the session later.
            This is especially useful for long-running commands.
        """),
        Argument('--server', help="""
            Server to run management command on.
            Defaults to first server under django_manage inventory group
        """, default='django_manage[0]'),
        Argument('--release', help="""
            Name of release to run under.
            E.g. '2018-04-13_18.16'.
            If none is specified, the `current` release will be used.
        """),
        Argument('--tee', dest='tee_file', help="""
            Tee output to the screen and to this file on the remote machine
        """)
    )

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        public_vars = environment.public_vars
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        cchq_user = public_vars.get('cchq_user', 'cchq')
        deploy_env = environment.meta_config.deploy_env
        # the paths here are redundant with ansible/group_vars/all.yml
        if args.release:
            code_dir = '/home/{cchq_user}/www/{deploy_env}/releases/{release}'.format(
                cchq_user=cchq_user, deploy_env=deploy_env, release=args.release)
        else:
            code_dir = '/home/{cchq_user}/www/{deploy_env}/current'.format(
                cchq_user=cchq_user, deploy_env=deploy_env)

        def _get_ssh_args(remote_command):
            return ['sudo -iu {cchq_user} bash -c {remote_command}'.format(
                cchq_user=cchq_user,
                remote_command=shlex_quote(remote_command),
            )]

        if args.tee_file:
            rc = Ssh(self.parser).run(args, _get_ssh_args(
                'cd {code_dir}; [[ -f {tee_file} ]]'
                .format(code_dir=code_dir, tee_file=shlex_quote(args.tee_file))
            ))
            if rc in (0, 1):
                file_already_exists = (rc == 0)
            else:
                return rc

            if file_already_exists:
                puts(color_error("Refusing to --tee to a file that already exists ({})".format(args.tee_file)))
                return 1

            tee_file_cmd = ' | tee {}'.format(shlex_quote(args.tee_file))
        else:
            tee_file_cmd = ''

        python_env = 'python_env-3.6'
        remote_command = (
            'cd {code_dir}; {python_env}/bin/python manage.py {args}{tee_file_cmd}'
            .format(
                python_env=python_env,
                cchq_user=cchq_user,
                code_dir=code_dir,
                args=' '.join(shlex_quote(arg) for arg in manage_args),
                tee_file_cmd=tee_file_cmd,
            )
        )
        if args.tmux:
            args.remote_command = remote_command
            return Tmux(self.parser).run(args, [])
        else:
            ssh_args = _get_ssh_args(remote_command)
            if manage_args and manage_args[0] in ["shell", "dbshell"]:
                # force ssh to allocate a pseudo-terminal
                ssh_args = ['-t'] + ssh_args
            return Ssh(self.parser).run(args, ssh_args)
