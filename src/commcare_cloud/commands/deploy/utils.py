from datetime import datetime
from github.GithubException import GithubException
import pytz

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.colors import color_summary, color_error
from commcare_cloud.user_utils import get_default_username


def create_release_tag(environment, repo, diff):
    if environment.fab_settings_config.tag_deploy_commits:
        try:
            repo.create_git_ref(
                ref='refs/tags/{}-{}-deploy'.format(
                    environment.new_release_name(),
                    environment.name),
                sha=diff.deploy_commit,
            )
        except GithubException as e:
            print(color_error(f"Error creating release tag: {e}"))


def announce_deploy_start(environment, service_name, commcare_rev=None):
    user = get_default_username()
    is_nonstandard_deploy_time = not within_maintenance_window(environment)
    is_non_default_branch = (
        commcare_rev != environment.fab_settings_config.default_branch and
        commcare_rev is not None
    )
    env_name = environment.meta_config.deploy_env
    subject = f"{user} has initiated a {service_name} deploy to {env_name}"
    prefix = ""
    if is_nonstandard_deploy_time:
        subject += " outside maintenance window"
        prefix = "ATTENTION: "
    if is_non_default_branch:
        subject += f" with non-default branch '{commcare_rev}'"
        prefix = "ATTENTION: "
    subject = f"{prefix}{subject}"

    send_email(
        environment,
        subject=subject,
    )


def announce_deploy_failed(environment, service_name):
    send_email(
        environment,
        subject=f"{service_name} deploy to {environment.name} failed",
    )


def announce_deploy_success(environment, service_name, diff_ouptut):
    recipient = environment.public_vars.get('daily_deploy_email', None)
    send_email(
        environment,
        subject=f"{service_name} deploy successful - {environment.name}",
        message=diff_ouptut,
        to_admins=True,
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

def within_maintenance_window(environment):
    window = environment.fab_settings_config.acceptable_maintenance_window
    if window:
        d = datetime.now(pytz.timezone(window['timezone']))
        return window['hour_start'] <= d.hour < window['hour_end']
    return True
