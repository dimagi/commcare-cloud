import os
import sys
from commcare_cloud.commands.command_base import CommandBase
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
        print(self.lookup_server_address(args))


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
        print(cmd)
        os.execvp(self.command, cmd_parts)


class Mosh(Ssh):
    command = 'mosh'
    help = "Connect to a remote host with mosh"
