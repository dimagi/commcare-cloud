from commcare_cloud.alias import commcare_cloud
from commcare_cloud.colors import color_summary
from commcare_cloud.commands.terraform.aws import get_default_username


def announce_deploy_start(environment, system_name):
    send_email(
        environment,
        subject="{user} has initiated a {system_name} deploy to {environment}".format(
            user=get_default_username(),
            system_name=system_name,
            environment=environment.meta_config.deploy_env,
        ),
    )


def announce_deploy_failed(environment):
    send_email(
        environment,
        subject=f"Formplayer deploy to {environment.name} failed",
    )


def announce_deploy_success(environment, diff_ouptut):
    recipient = environment.public_vars.get('daily_deploy_email', None)
    send_email(
        environment,
        subject=f"Formplayer deploy successful - {environment.name}",
        message=diff_ouptut,
        to_admins=not recipient,
        recipients=[recipient] if recipient else None
    )


def send_email(environment, subject, message='', to_admins=True, recipients=None):
    """
    Call a Django management command to send an email.

    :param environment: The Environement object
    :param subject: Email subject
    :param message: Email message
    :param to_admins: True if mail should be sent to Django admins
    :param recipients: List of additional addresses to send mail to
    """
    if environment.fab_settings_config.email_enabled:
        print(color_summary(f">> Sending email: {subject}"))
        args = [
            message,
            '--subject', subject,
            '--html',
        ]
        if to_admins:
            args.append('--to-admins')
        if recipients:
            if isinstance(recipients, list):
                recipients = ','.join(recipients)

            args.extend(['--recipients', recipients])

        commcare_cloud(
            environment.name, 'django-manage', '--quiet', 'send_email',
            *args,
            show_command=False
        )
