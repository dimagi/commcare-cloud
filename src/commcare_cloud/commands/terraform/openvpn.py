from commcare_cloud.commands.ansible.ansible_playbook import run_ansible_playbook, \
    AnsiblePlaybook, _AnsiblePlaybookAlias
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.inventory_lookup.inventory_lookup import Ssh
from commcare_cloud.environment.main import get_environment


class OpenvpnActivateUser(_AnsiblePlaybookAlias):
    command = 'openvpn-activate-user'
    help = """
    Give a OpenVPN user a temporary password (the ansible user password)

    to allow the user to connect to the VPN, log in, and change their password using

    ```
    cchq <env> openvpn-claim-user
    ```
    """

    arguments = _AnsiblePlaybookAlias.arguments + (
        Argument('vpn_user', help="""
            The user to activate.

            Must be one of the defined ssh users defined for the environment.
        """),
    )

    def run(self, args, unknown_args):
        args.playbook = 'openvpn_playbooks/activate_vpn_user.yml'
        unknown_args += ('-e', 'vpn_user={}'.format(args.vpn_user))
        return AnsiblePlaybook(self.parser).run(args, unknown_args, always_skip_check=True)


class OpenvpnClaimUser(_AnsiblePlaybookAlias):
    command = 'openvpn-claim-user'
    help = """
    Claim an OpenVPN user as your own, setting its password
    """

    arguments = _AnsiblePlaybookAlias.arguments + (
        Argument('vpn_user', help="""
            The user to claim.

            Must be one of the defined ssh users defined for the environment.
        """),
    )

    def run(self, args, unknown_args):
        args.playbook = 'openvpn_playbooks/mark_vpn_user_claimed.yml'
        unknown_args += ('-e', 'vpn_user={}'.format(args.vpn_user))
        return AnsiblePlaybook(self.parser).run(args, unknown_args, always_skip_check=True)
