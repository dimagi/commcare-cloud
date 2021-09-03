from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import socket
import subprocess
import sys

from clint.textui import puts
from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command, ask
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.environment.main import get_environment
from commcare_cloud.user_utils import get_ssh_username
from ..ansible.helpers import get_default_ssh_options_as_cmd_parts
from ..terraform.aws import aws_sign_in, is_aws_env, is_ec2_instance_in_account, \
    is_session_manager_plugin_installed
from ...alias import commcare_cloud

from ...colors import color_error, color_notice, color_link
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
            return lookup_server_address(args.env_name, args.server)
        except Exception as e:
            self.parser.error("\n" + str(e))

    def run(self, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print(self.lookup_server_address(args))


def lookup_server_address(env_name, server):
    if not server:
        return get_monolith_address(env_name)
    return get_server_address(env_name, server)


class _Ssh(Lookup):

    arguments = Lookup.arguments + (
        Argument("--quiet", action='store_true', default=False, help="""
            Don't output the command to be run.
        """),
    )

    def run(self, args, ssh_args, env_vars=None):
        if args.server == '-':
            args.server = 'django_manage[0]'
        address = self.lookup_server_address(args)
        if ':' in address:
            address, port = address.split(':')
            ssh_args = ['-p', port] + ssh_args
        if '@' in address:
            username, address = address.split('@', 1)
            username = get_ssh_username(address, args.env_name, requested_username=username)
        elif '@' not in address:
            username = get_ssh_username(address, args.env_name)
        address = f"{username}@{address}"
        cmd_parts = [self.command, address, '-t'] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        if not args.quiet:
            print_command(cmd)
        return subprocess.call(cmd_parts, **({'env': env_vars} if env_vars else {}))


class Ssh(_Ssh):
    command = 'ssh'
    help = """
    Connect to a remote host with ssh.

    This will also automatically add the ssh argument `-A`
    when `<server>` is `control`.

    All trailing arguments are passed directly to `ssh`.
    """

    run_setup_on_control_by_default = False

    def run(self, args, ssh_args):
        environment = get_environment(args.env_name)
        use_aws_ssm_with_instance_id = None
        env_vars = None

        if 'control' in split_host_group(args.server).group and '-A' not in ssh_args:
            # Always include ssh agent forwarding on control machine
            ssh_args = ['-A'] + ssh_args

            if os.environ.get('COMMCARE_CLOUD_USE_AWS_SSM') == '1' and \
                    is_aws_env(environment) and \
                    not is_ec2_instance_in_account(environment.aws_config.sso_config.sso_account_id):
                if not is_session_manager_plugin_installed():
                    puts(color_error("Before you can use AWS SSM to connect, you must install the AWS session-manager-plugin"))
                    puts(f"{color_notice('See ')}{color_link('https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html')}{color_notice(' for instructions.')}")
                    return -1
                use_aws_ssm_with_instance_id = environment.get_host_vars(environment.groups['control'][0])['ec2_instance_id']
                env_vars = os.environ.copy()
                env_vars.update({'AWS_PROFILE': aws_sign_in(environment)})

        ssh_args = get_default_ssh_options_as_cmd_parts(environment, original_ssh_args=ssh_args, use_aws_ssm_with_instance_id=use_aws_ssm_with_instance_id) + ssh_args
        return super(Ssh, self).run(args, ssh_args, env_vars=env_vars)


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

    run_setup_on_control_by_default = False

    arguments = _Ssh.arguments + (
        Argument('remote_command', nargs='?', help="""
            Command to run in the tmux.
            If a command is specified, then it will always run in a new window.
            If a command is *not* specified, then it will rejoin the most
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
                r'tmux attach \; new-window -n {window_name} {remote_command} '
                r'|| tmux new -n {window_name} {remote_command}'
                .format(
                    remote_command="sudo -iu {} -- sh -c {}".format(cchq_user, remote_command),
                    window_name=window_name_expression,
                )
            ] + ssh_args
        else:
            ssh_args = [
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

    run_setup_on_control_by_default = False

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
        """),
        Argument("--quiet", action='store_true', default=False, help="""
            Don't output the command to be run.
        """),
    )

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        if args.release:
            code_dir = environment.remote_conf.release(args.release)
        else:
            code_dir = environment.remote_conf.code_current

        def _get_ssh_args(remote_command):
            return ['sudo -iu {cchq_user} bash -c {remote_command}'.format(
                cchq_user=environment.remote_conf.cchq_user,
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
                cchq_user=environment.remote_conf.cchq_user,
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
            return Ssh(self.parser).run(args, ssh_args)


class ForwardPort(CommandBase):
    command = 'forward-port'
    help = """
    Port forward to access a remote admin console
    """
    _SERVICES = {
        'flower': ('celery[0]', 5555, '/'),
        'couch': ('couchdb2_proxy[0]', 25984, '/_utils/'),
        'elasticsearch': ('elasticsearch[0]', 9200, '/'),
    }

    arguments = (
        Argument('service', choices=_SERVICES.keys(), help=f"""
            The remote service to port forward. Must be one of {','.join(sorted(_SERVICES.keys()))}.
        """),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        nice_name = environment.terraform_config.account_alias
        remote_host_key, remote_port, url_path = self._SERVICES[args.service]
        loopback_address = f'127.0.{environment.terraform_config.vpc_begin_range}'
        remote_host = lookup_server_address(args.env_name, remote_host_key)
        local_port = self.get_random_available_port()

        while not self.is_loopback_address_set_up(loopback_address):
            puts(color_error('To make this work you will need to run set up a special loopback address on your local machine:'))
            puts(color_notice(f'  - Mac: Run `sudo ifconfig lo0 alias {loopback_address}`.'))
            puts(color_notice(f'  - Linux: Run `sudo ip addr add {loopback_address}/8 dev lo`.'))
            if not ask("Follow the instructions above or type n to exit. Ready to continue?"):
                return -1
            puts()

        while not self.is_etc_hosts_alias_set_up(loopback_address, nice_name):
            puts(color_error('Okay, now the last step is to set up a special alias in your /etc/hosts:'))
            puts(color_notice(f'  - Edit /etc/hosts (e.g. `sudo vim /etc/hosts`) and add the line `{loopback_address} {nice_name}` to it.'))
            if not ask("Follow the instructions above or type n to exit. Ready to continue?"):
                return -1
            puts()

        puts(color_notice(f'You should now be able to reach {args.env_name} {args.service} at {color_link(f"http://{nice_name}:{local_port}{url_path}")}.'))
        puts(f'Interrupt with ^C to stop port-forwarding and exit.')
        puts()
        try:
            return commcare_cloud(args.env_name, 'ssh', 'control', '-NL', f'{loopback_address}:{local_port}:{remote_host}:{remote_port}')
        except KeyboardInterrupt:
            puts()
            puts('Connection closed.')
            # ^C this is how we expect the user to terminate this command, so no need to print a stacktrace
            return 0

    @staticmethod
    def is_loopback_address_set_up(loopback_address):
        try:
            # Use either ifconfig or ip, whichever is available
            subprocess.check_output(f'ping -c 1 -W 1 {shlex_quote(loopback_address)}', shell=True)
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    @staticmethod
    def is_etc_hosts_alias_set_up(loopback_address, nice_name):
        try:
            resolved = socket.gethostbyname(nice_name)
        except socket.gaierror:
            return False
        else:
            return resolved == loopback_address

    @staticmethod
    def get_random_available_port():
        try:
            tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp.bind(('', 0))
            addr, port = tcp.getsockname()
            return port
        finally:
            tcp.close()
