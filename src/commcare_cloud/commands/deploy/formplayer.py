from commcare_cloud.alias import commcare_cloud
from commcare_cloud.commands.ansible import ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.terraform.aws import get_default_username


def deploy_formplayer(environment, args):
    announce_formplayer_deploy_start(environment)

    rc = run_ansible_playbook_command(environment, args)
    if rc != 0:
        return rc
    rc = commcare_cloud(
        args.env_name, 'run-shell-command', 'formplayer',
        ('supervisorctl reread; '
         'supervisorctl update {project}-{deploy_env}-formsplayer-spring; '
         'supervisorctl restart {project}-{deploy_env}-formsplayer-spring').format(
            project='commcare-hq',
            deploy_env=environment.meta_config.deploy_env,
        ), '-b',
    )
    if rc != 0:
        return rc


def run_ansible_playbook_command(environment, args):
    skip_check = True
    environment.create_generated_yml()
    ansible_context = AnsibleContext(args)
    return ansible_playbook.run_ansible_playbook(
        environment, 'deploy_stack.yml', ansible_context,
        skip_check=skip_check, quiet=skip_check, always_skip_check=skip_check, limit='formplayer',
        use_factory_auth=False, unknown_args=('--tags=formplayer_deploy',),
        respect_ansible_skip=True,
    )


def announce_formplayer_deploy_start(environment):
    mail_admins(
        environment,
        subject="{user} has initiated a formplayer deploy to {environment}.".format(
            user=get_default_username(),
            environment=environment.meta_config.deploy_env,
        ),
        message='',
    )


def mail_admins(environment, subject, message):
    if environment.fab_settings_config.email_enabled:
        commcare_cloud(
            environment.name, 'django-manage', 'mail_admins',
            '--subject', subject,
            message,
            '--environment', environment.meta_config.deploy_env
        )

