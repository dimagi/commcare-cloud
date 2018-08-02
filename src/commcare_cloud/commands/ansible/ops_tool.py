import collections
import paramiko
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

    def run(self, host_address):
        """

        :param host_address: Address of host where command should be run.
        :type host_address: str
        :return: output of command in list format
        """
        output = None
        try:
            ssh = paramiko.SSHClient()
            ssh.load_host_keys(self.known_host_file)
            ssh.connect(host_address, username=self.user_name, password=self.password)

            stdin, stdout, stderr = ssh.exec_command(self.privileged_command, get_pty=True)
            stdin.write(self.password + '\n')
            stdin.flush()
            output = stdout.read().splitlines()
            if output[0].startswith('[sudo]'):
                output = output[1:]  # Ignore sudo prompt.
        except paramiko.ssh_exception.SSHException as pe:
            print(host_address + " not known_host " + self.known_host_file + ", or SSH failed"
                  "\nRun `cchq <env> update-local-known-hosts`")
            print(pe)
            exit(1)
        return output

    # def run_parallel_command(self, hosts):
    #     from fabric.api import execute, sudo, env, parallel
    #     if env.ssh_config_path and os.path.isfile(os.path.expanduser(env.ssh_config_path)):
    #         env.use_ssh_config = True
    #     env.forward_agent = True
    #     # pass `-E` to sudo to preserve environment for ssh agent forwarding
    #     env.sudo_prefix = "sudo -SE -p '%(sudo_prompt)s' "
    #     env.user = self.user_name
    #     env.password = self.password
    #     env.hosts = hosts
    #     env.warn_only = True
    #
    #     @parallel(pool_size=10)
    #     def _task():
    #         res = sudo(self.privileged_command)
    #         return res.return_code
    #
    #     res = execute(_task)
    #     non_zero_returns = [ret for ret in res.values() if ret]
    #     return non_zero_returns[0] if non_zero_returns else 0
    #

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
        dbs_present_in_host = self.get_present_dbs(args)   # Database that are in host

          # Print Logic
        if args.compare:
            # Printing Comparison
            for host_address in dbs_present_in_host.keys():
                print(host_address + ":")
                print(" " * 4 + "Expected Databases:")
                for database in dbs_expected_on_host[host_address]:
                    print(" " * 8 + "- " + database)

                print(" " * 4 + "Additional Databases:")
                for database in dbs_present_in_host[host_address]:
                    if database not in dbs_expected_on_host[host_address]:
                        print(" " * 8 + "- " + database)
        else:
            # Print Default
            for host_address in dbs_expected_on_host.keys():
                print(host_address + ":")
                print(" " * 4 + "Expected Databases:")
                for database in dbs_expected_on_host[host_address]:
                    print(" " * 8 + "- " + database)

    def get_present_dbs(self, args):
        dbs_present_in_host = collections.defaultdict(list)
        args.server = 'postgresql'
        ansible_username = 'ansible'
        command = "sudo -iu postgres python /usr/local/sbin/db-tools.py  --list-all"

        environment = get_environment(args.env_name)
        ansible_password = environment.get_ansible_user_password()
        ansible_password = 'ansible'
        host_addresses = get_instance_group(args.env_name, args.server)
        known_host_file = environment.paths.known_hosts

        privileged_command = PrivilegedCommands(ansible_username, ansible_password, known_host_file, command)

        privileged_command.run_parallel_command(host_addresses)

        # List from Postgresql query.
        for host_address in host_addresses:
            output = privileged_command.run(host_address)
            for database in output:
                dbs_present_in_host[host_address].append(database)

        return dbs_present_in_host

    def get_expected_dbs(self,args):
        environment = get_environment(args.env_name)
        dbs_expected_on_host = collections.defaultdict(list)
        dbs = environment.postgresql_config.to_generated_variables()['postgresql_dbs']['all']
        for db in dbs:
            dbs_expected_on_host[db['host']].append(db['name'])
        return dbs_expected_on_host

