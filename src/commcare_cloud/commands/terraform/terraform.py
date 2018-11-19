from __future__ import print_function

import json
import os
import subprocess

from clint.textui import puts, colored
from six.moves import shlex_quote

from commcare_cloud.cli_utils import print_command
from commcare_cloud.commands.command_base import CommandBase, Argument
from commcare_cloud.commands.terraform.aws import aws_sign_in, get_default_username, \
    print_help_message_about_the_commcare_cloud_default_username_env_var
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment
from commcare_cloud.environment.paths import TERRAFORM_DIR


class Terraform(CommandBase):
    command = 'terraform'
    help = "Run terraform for this env with the given arguments"

    arguments = (
        Argument('--skip-secrets', action='store_true', help="""
            Skip regenerating the secrets file.

            Good for not having to enter vault password again.
        """),
        Argument('--username', default=get_default_username(), help="""
            The username of the user whose public key will be put on new servers.

            Normally this would be _your_ username.
            Defaults to the value of the COMMCARE_CLOUD_DEFAULT_USERNAME environment variable
            or else the username of the user running the command.
        """),
    )

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        run_dir = environment.paths.get_env_file_path('.generated-terraform')
        modules_dir = os.path.join(TERRAFORM_DIR, 'modules')
        modules_dest = os.path.join(run_dir, 'modules')
        if not os.path.isdir(run_dir):
            os.mkdir(run_dir)
        if not os.path.isdir(run_dir):
            os.mkdir(run_dir)
        if not (os.path.exists(modules_dest) and os.readlink(modules_dest) == modules_dir):
            os.symlink(modules_dir, modules_dest)

        if args.username != get_default_username():
            print_help_message_about_the_commcare_cloud_default_username_env_var(args.username)

        key_name = args.username

        try:
            generate_terraform_entrypoint(environment, key_name, run_dir)
        except UnauthorizedUser as e:
            allowed_users = environment.users_config.dev_users.present
            puts(colored.red(
                "Unauthorized user {}.\n\n"
                "Use COMMCARE_CLOUD_DEFAULT_USERNAME or --username to pass in one of the allowed ssh users:{}"
                .format(e.username, '\n  - '.join([''] + allowed_users))))
            return -1

        if not args.skip_secrets and unknown_args and unknown_args[0] in ('plan', 'apply'):
            rds_password = environment.get_vault_variables()['secrets']['POSTGRES_USERS']['root']['password']
            with open(os.path.join(run_dir, 'secrets.auto.tfvars'), 'w') as f:
                print('rds_password = {}'.format(json.dumps(rds_password)), file=f)

        env_vars = {'AWS_PROFILE': aws_sign_in(environment.terraform_config.aws_profile)}
        all_env_vars = os.environ.copy()
        all_env_vars.update(env_vars)
        cmd_parts = ['terraform'] + unknown_args
        cmd = ' '.join(shlex_quote(arg) for arg in cmd_parts)
        print_command('cd {}; {} {}; cd -'.format(
            run_dir,
            ' '.join('{}={}'.format(key, value) for key, value in env_vars.items()),
            cmd,
        ))
        return subprocess.call(cmd, shell=True, env=all_env_vars, cwd=run_dir)


class UnauthorizedUser(Exception):
    def __init__(self, username):
        self.username = username


def generate_terraform_entrypoint(environment, key_name, run_dir):
    context = environment.terraform_config.to_json()
    if key_name not in environment.users_config.dev_users.present:
        raise UnauthorizedUser(key_name)

    context.update({
        'users': [{
            'username': username,
            'public_key': environment.get_authorized_key(username)
        } for username in environment.users_config.dev_users.present],
        'key_name': key_name,
    })
    template_root = os.path.join(os.path.dirname(__file__), 'templates')
    for template_file, output_file in (
            ('terraform.tf.j2', 'terraform.tf'),
            ('commcarehq.tf.j2', 'commcarehq.tf'),
            ('postgresql.tf.j2', 'postgresql.tf'),
            ('variables.tf.j2', 'variables.tf'),
            ('terraform.tfvars.j2', 'terraform.tfvars'),
    ):
        with open(os.path.join(run_dir, output_file), 'w') as f:
            f.write(render_template(template_file, context, template_root).encode('utf-8'))
