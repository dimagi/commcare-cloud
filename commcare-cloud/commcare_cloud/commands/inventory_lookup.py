import os
import sys
from commcare_cloud.getinventory import get_server_address


class Lookup(object):
    command = 'lookup'
    help = "Lookup remote hostname or IP address"

    @classmethod
    def make_parser(cls, parser):
        cls.parser = parser
        parser.add_argument("server",
            help="Server name/group: postgresql, proxy, webworkers, ... The server "
                 "name/group may be prefixed with 'username@' to login as a specific "
                 "user and may be terminated with ':<n>' to choose one of "
                 "multiple servers if there is more than one in the group. "
                 "For example: webworkers:0 will pick the first webworker.")

    @classmethod
    def lookup_server_address(cls, args):
        def exit(message):
            cls.parser.error("\n" + message)
        return get_server_address(args.environment, args.server, exit)

    @classmethod
    def run(cls, args, unknown_args):
        if unknown_args:
            sys.stderr.write(
                "Ignoring extra argument(s): {}\n".format(unknown_args)
            )
        print(cls.lookup_server_address(args))


class Ssh(Lookup):
    command = 'ssh'
    help = "Connect to a remote host with ssh"

    @classmethod
    def run(cls, args, ssh_args):
        address = cls.lookup_server_address(args)
        if ':' in address:
            address, port = address.split(':')
            ssh_args = ['-p', port] + ssh_args
        cmd_parts = [cls.command, address] + ssh_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print(cmd)
        os.execvp(cls.command, cmd_parts)


class Mosh(Ssh):
    command = 'mosh'
    help = "Connect to a remote host with mosh"
