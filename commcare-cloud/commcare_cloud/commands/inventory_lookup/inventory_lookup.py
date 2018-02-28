from __future__ import print_function
import os
import sys

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import get_public_vars
from .getinventory import get_server_address
from six.moves import shlex_quote


class Lookup(CommandBase):
    command = 'lookup'
    help = "Lookup remote hostname or IP address"

    def make_parser(self):
        self.parser.add_argument("server",
            help="Server name/group: postgresql, proxy, webworkers, ... The server "
                 "name/group may be prefixed with 'username@' to login as a specific "
                 "user and may be terminated with ':<n>' to choose one of "
                 "multiple servers if there is more than one in the group. "
                 "For example: webworkers:0 will pick the first webworker.")

    def lookup_server_address(self, args):
        def exit(message):
            self.parser.error("\n" + message)
        return get_server_address(args.environment, args.server, exit)

    def run(self, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print_command(self.lookup_server_address(args))


class Ssh(Lookup):
    command = 'ssh'
    help = "Connect to a remote host with ssh"

    def run(self, args, ssh_args):
        address = self.lookup_server_address(args)
        if ':' in address:
            address, port = address.split(':')
            ssh_args = ['-p', port] + ssh_args
        cmd_parts = [self.command, address] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command(cmd)
        os.execvp(self.command, cmd_parts)


class Mosh(Ssh):
    command = 'mosh'
    help = "Connect to a remote host with mosh"


class DjangoManage(CommandBase):
    command = 'django-manage'
    help = ("Run a django management command. "
            "`commcare-cloud <env> django-manage ...` "
            "runs `./manage.py ...` on the first webworker of <env>. "
            "Omit <command> to see a full list of possible commands.")

    def make_parser(self):
        pass

    def run(self, args, manage_args):
        public_vars = get_public_vars(args.environment)
        # the default 'cchq' is redundant with ansible/group_vars/all.yml
        cchq_user = public_vars.get('cchq_user', 'cchq')
        deploy_env = public_vars['deploy_env']
        # the paths here are redundant with ansible/group_vars/all.yml
        code_current = '/home/{cchq_user}/www/{deploy_env}/current'.format(
            cchq_user=cchq_user, deploy_env=deploy_env)
        remote_command = (
            'sudo -u {cchq_user} {code_current}/python_env/bin/python {code_current}/manage.py {args}'
            .format(cchq_user=cchq_user, code_current=code_current, args=' '.join(shlex_quote(arg) for arg in manage_args))
        )
        args.server = 'webworkers:0'
        Ssh(self.parser).run(args, [remote_command])
