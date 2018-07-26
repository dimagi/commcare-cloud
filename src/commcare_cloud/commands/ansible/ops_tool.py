import paramiko
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.inventory_lookup.getinventory import get_instance_group
from commcare_cloud.commands.inventory_lookup.inventory_lookup import Lookup
from commcare_cloud.environment.main import get_environment

NON_POSITIONAL_ARGUMENTS = (
    Argument('-b', '--become', action='store_true', help=(
        "run operations with become (implies vault password prompting if necessary)"
    ), include_in_docs=False),
    Argument('--become-user', help=(
        "run operations as this user (default=root)"
    ), include_in_docs=False),
    shared_args.SKIP_CHECK_ARG,
    shared_args.FACTORY_AUTH_ARG,
    shared_args.QUIET_ARG,
    shared_args.STDOUT_CALLBACK_ARG,
)


class PrivilegedCommands():
    def __init__(self, user_name, password, privleged_command):
        self.user_name = user_name
        self.password = password
        self.privileged_command = privleged_command if privleged_command.startswith('sudo') \
            else 'sudo ' + privleged_command

    def run(self, host_address):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host_address, username=self.user_name, password=self.password)
        stdin, stdout , stderr = ssh.exec_command(self.privileged_command, get_pty=True)
        stdin.write(self.password + '\n')
        stdin.flush()
        print(stdout.read())
        return stdout


class ListDatabases(Lookup):
    command = 'list-databases'
    help = """

    Example:

    To list all database on a particular server or group

    ```
    commcare-cloud staging list-databases <group_name|server_name>
    ```
    """

    def run(self, args, manage_args):
        environment = get_environment(args.env_name)
        ansible_username = 'ansible'
        ansible_password = environment.get_ansible_user_password()
        host_addresses = get_instance_group(args.env_name, args.server)
        command = "sudo -iu postgres python /usr/local/sbin/db-tools.py  --list-all"
        privileged_command = PrivilegedCommands(ansible_username, ansible_password, command)
        for host_address in host_addresses:
            print("Database in " + host_address + " are: ")
            output = privileged_command.run(host_address)
            for database in output.read().splitlines():
                print(database)


