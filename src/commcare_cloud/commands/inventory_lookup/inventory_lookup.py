from __future__ import print_function
import os
import sys

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.main import get_environment
from .getinventory import get_server_address, get_monolith_address
from six.moves import shlex_quote


class Lookup(CommandBase):
    command = 'lookup'
    help = "Lookup remote hostname or IP address"

    def modify_parser(self):
        self.parser.add_argument("server", nargs="?",
            help="Server name/group: postgresql, proxy, webworkers, ... The server "
                 "name/group may be prefixed with 'username@' to login as a specific "
                 "user and may be terminated with ':<n>' to choose one of "
                 "multiple servers if there is more than one in the group. "
                 "For example: webworkers:0 will pick the first webworker. May also"
                 "be ommitted for environments with only a single server.")

    def lookup_server_address(self, args):
        def exit(message):
            self.parser.error("\n" + message)
        if not args.server:
            return get_monolith_address(args.env_name, exit)
        return get_server_address(args.env_name, args.server, exit)

    def run(self, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print_command(self.lookup_server_address(args))


class _Ssh(Lookup):

    def run(self, args, ssh_args):
        address = self.lookup_server_address(args)
        if ':' in address:
            address, port = address.split(':')
            ssh_args = ['-p', port] + ssh_args
        cmd_parts = [self.command, address] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        os.execvp(self.command, cmd_parts)


class Ssh(_Ssh):
    command = 'ssh'
    help = "Connect to a remote host with ssh"

    def run(self, args, ssh_args):
        if args.server == 'control' and '-A' not in ssh_args:
            # Always include ssh agent forwarding on control machine
            ssh_args = ['-A'] + ssh_args
        ukhf = "UserKnownHostsFile="
        if not any(a.startswith((ukhf, "-o" + ukhf)) for a in ssh_args):
            environment = get_environment(args.env_name)
            ssh_args = ["-o", ukhf + environment.paths.known_hosts] + ssh_args
        super(Ssh, self).run(args, ssh_args)


class Mosh(_Ssh):
    command = 'mosh'
    help = "Connect to a remote host with mosh"

    def run(self, args, ssh_args):
        if args.server == 'control' or '-A' in ssh_args:
            print("! mosh does not support ssh agent forwarding, using ssh instead.",
                  file=sys.stderr)
            Ssh(self.parser).run(args, ssh_args)
        super(Mosh, self).run(args, ssh_args)


class Tmux(_Ssh):
    command = 'tmux'
    help = "Connect to a remote host with ssh and open a tmux session"

    def modify_parser(self):
        self.parser.add_argument('server',
                                 help="server to run tmux session on. "
                                      "Use '-' to for default (webworkers:0)")
        self.parser.add_argument('remote_command', nargs='?',
                                 help="command to run in new tmux session")

    def run(self, args, ssh_args):
        environment = get_environment(args.env_name)
        public_vars = environment.public_vars
        if args.server == '-':
            args.server = 'webworkers:0'
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        cchq_user = public_vars.get('cchq_user', 'cchq')
        # Name tabs like "droberts (2018-04-13)"
        window_name_expression = '"`whoami` (`date +%Y-%m-%d`)"'
        if args.remote_command:
            ssh_args = [
                '-t',
                r'sudo -iu {cchq_user} tmux attach \; new-window -n {window_name} {remote_command} '
                r'|| sudo -iu {cchq_user} tmux new -n {window_name} {remote_command}'
                .format(
                    cchq_user=cchq_user,
                    remote_command=shlex_quote('{} ; bash'.format(args.remote_command)),
                    window_name=window_name_expression,
                )
            ] + ssh_args
        else:
            ssh_args = [
                '-t',
                'sudo -iu {cchq_user} tmux attach || sudo -iu {cchq_user} tmux new -n {window_name}'
                .format(cchq_user=cchq_user, window_name=window_name_expression)
            ]
        Ssh(self.parser).run(args, ssh_args)


class DjangoManage(CommandBase):
    command = 'django-manage'
    help = ("Run a django management command. "
            "`commcare-cloud <env> django-manage ...` "
            "runs `./manage.py ...` on the first webworker of <env>. "
            "Omit <command> to see a full list of possible commands.")

    def modify_parser(self):
        self.parser.add_argument('--tmux', action='store_true', default=False, help="Run this command in a tmux and stay connected")
        self.parser.add_argument('--release', help=(
            "Name of release to run under. E.g. '2018-04-13_18.16'"))

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
        remote_command = (
            '{code_dir}/python_env/bin/python {code_dir}/manage.py {args}'
            .format(
                cchq_user=cchq_user,
                code_dir=code_dir,
                args=' '.join(shlex_quote(arg) for arg in manage_args),
            )
        )
        args.server = 'webworkers:0'
        if args.tmux:
            args.remote_command = remote_command
            Tmux(self.parser).run(args, [])
        else:
            ssh_args = ['sudo -u {cchq_user} {remote_command}'.format(
                cchq_user=cchq_user,
                remote_command=remote_command,
            )]
            if manage_args and manage_args[0] in ["shell", "dbshell"]:
                # force ssh to allocate a pseudo-terminal
                ssh_args = ['-t'] + ssh_args
            Ssh(self.parser).run(args, ssh_args)
