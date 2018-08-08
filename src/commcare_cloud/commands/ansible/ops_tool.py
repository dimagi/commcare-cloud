import collections
import os
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.inventory_lookup.getinventory import get_instance_group
from commcare_cloud.environment.main import get_environment


class PrivilegedCommands():
    """
    This Class allows to execute sudo commands over ssh.
    """
    def __init__(self, user_name, password, known_host_file, privleged_command):
        """

        :param user_name: Username to login with
        :param password: Password of the user
        :param known_host_file: Path to the known host file
        :param privleged_command: command to execute (This command will be executed using sudo. )
        """
        self.user_name = user_name
        self.password = password
        self.privileged_command = privleged_command if privleged_command.startswith('sudo') \
            else 'sudo ' + privleged_command
        self.known_host_file = known_host_file

    def run_parallel_command(self, hosts):
        from fabric.api import execute, sudo, env
        if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
            env.use_ssh_config = True
        env.forward_agent = True
        # pass `-E` to sudo to preserve environment for ssh agent forwarding
        env.sudo_prefix = "sudo -SE -p '%(sudo_prompt)s' "
        env.user = self.user_name
        env.password = self.password
        env.hosts = hosts
        env.warn_only = True

        def _task():
            result = sudo(self.privileged_command)
            return result

        res = execute(_task)
        return res


class ListDatabases(CommandBase):
    command = 'list-postgresql-dbs'
    help = """

    Example:

    To list all database on a particular environment.

    ```
    commcare-cloud <ev> list-databases
    ```
    """

    arguments = (
        Argument('--compare', action='store_true', help=(
            "Gives additional databases on the server."
        )),
    )

    def run(self, args, manage_args,compare=None):
        # Initialize variables
        dbs_expected_on_host = self.get_expected_dbs(args)  # Database that should be in host
        if args.compare:
            dbs_present_in_host = self.get_present_dbs(args)  # Database that are in host

        # Print Logic
        # Printing Comparison
        for host_address in dbs_expected_on_host.keys():
            print(host_address + ":")
            print(" " * 4 + "Expected Databases:")
            for database in dbs_expected_on_host[host_address]:
                print(" " * 8 + "- " + database)
            if args.compare:
                print(" " * 4 + "Additional Databases:")
                for database in dbs_present_in_host[host_address]:
                    if database not in dbs_expected_on_host[host_address]:
                        print(" " * 8 + "- " + database)

    @staticmethod
    def get_present_dbs( args):
        dbs_present_in_host = collections.defaultdict(list)
        args.server = 'postgresql'
        ansible_username = 'ansible'
        command = "sudo -iu postgres python /usr/local/sbin/db-tools.py  --list-all"

        environment = get_environment(args.env_name)
        ansible_password = environment.get_ansible_user_password()
        host_addresses = get_instance_group(args.env_name, args.server)
        known_host_file = environment.paths.known_hosts

        privileged_command = PrivilegedCommands(ansible_username, ansible_password, known_host_file, command)

        present_db_op = privileged_command.run_parallel_command(host_addresses)

        # List from Postgresql query.

        for host_address in present_db_op.keys():
            dbs_present_in_host[host_address] = present_db_op[host_address].split("\n")

        return dbs_present_in_host

    @staticmethod
    def get_expected_dbs(args):
        environment = get_environment(args.env_name)
        dbs_expected_on_host = collections.defaultdict(list)
        dbs = environment.postgresql_config.to_generated_variables()['postgresql_dbs']['all']
        for db in dbs:
            dbs_expected_on_host[db['host']].append(db['name'])
        return dbs_expected_on_host

