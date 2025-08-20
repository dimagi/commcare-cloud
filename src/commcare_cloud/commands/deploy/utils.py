from datetime import datetime

import attr
from github.GithubException import GithubException
import pytz
from memoized import memoized

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_summary, color_error
from commcare_cloud.commands.deploy.slack import notify_slack_deploy_start, notify_slack_deploy_end
from commcare_cloud.user_utils import get_default_username


@attr.s
class DeployContext:
    # commcare or formplayer
    service_name = attr.ib()
    # branch or commit that's being deployed
    revision = attr.ib()
    diff = attr.ib()
    start_time = attr.ib()
    resume = attr.ib(default=False)
    metadata = attr.ib(factory=dict)

    @property
    @memoized
    def user(self):
        return get_default_username()

    def set_meta_value(self, key, value):
        self.metadata[key] = value

    def get_meta_value(self, key):
        return self.metadata.get(key)


def create_release_tag(environment, repo, diff):
    if environment.fab_settings_config.tag_deploy_commits:
        try:
            repo.create_git_ref(
                ref='refs/tags/{}-{}-deploy'.format(
                    environment.release_name,
                    environment.name),
                sha=diff.deploy_commit,
            )
        except GithubException as e:
            print(color_error(f"Error creating release tag: {e}"))


def record_deploy_start(environment, context):
    notify_slack_deploy_start(environment, context)
    send_deploy_start_email(environment, context)


def send_deploy_start_email(environment, context):
    is_nonstandard_deploy_time = not within_maintenance_window(environment)
    is_non_default_branch = (
        context.revision != environment.fab_settings_config.default_branch
        and context.revision is not None
    )
    env_name = environment.meta_config.deploy_env
    message = f"{context.user} has initiated a {context.service_name} deploy to {env_name}"
    prefix = ""
    if is_nonstandard_deploy_time:
        message += " outside maintenance window"
        prefix = "ATTENTION: "
    if is_non_default_branch:
        message += f" with non-default branch '{context.revision}'"
        prefix = "ATTENTION: "
    message = f"{prefix}{message}"

    send_email(
        environment,
        subject=message,
        message=message,
    )


def record_deploy_failed(environment, context):
    notify_slack_deploy_end(environment, context, is_success=False)
    message = f"{context.service_name} deploy to {environment.name} failed"
    send_email(
        environment,
        subject=message,
        message=message,
    )


def announce_deploy_success(environment, context):
    notify_slack_deploy_end(environment, context, is_success=True)
    recipient = environment.public_vars.get('daily_deploy_email', None)
    send_email(
        environment,
        subject=f"{context.service_name} deploy successful - {environment.name}",
        message=context.diff.get_email_diff(),
        to_admins=True,
        recipients=[recipient] if recipient else None
    )


def send_email(environment, subject, message, to_admins=True, recipients=None):
    """
    Call a Django management command to send an email.

    :param environment: The Environment object
    :param subject: Email subject
    :param message: Email message body
    :param to_admins: True if mail should be sent to Django admins
    :param recipients: List of additional addresses to send mail to
    """
    if not message:
        raise ValueError('Some cloud hosting providers require a message body')

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


def confirm_environment_time(environment, quiet=False):
    if within_maintenance_window(environment):
        return True
    window = environment.fab_settings_config.acceptable_maintenance_window
    d = datetime.now(pytz.timezone(window['timezone']))
    message = (
        "Whoa there bud! You're deploying '%s' outside the configured maintenance window. "
        "The current local time is %s.\n"
        "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
    ) % (environment.name, d.strftime("%-I:%M%p on %h. %d %Z"))
    return ask(message, quiet=quiet)


def within_maintenance_window(environment):
    window = environment.fab_settings_config.acceptable_maintenance_window
    if window:
        d = datetime.now(pytz.timezone(window['timezone']))
        return window['hour_start'] <= d.hour < window['hour_end']
    return True
