from datetime import datetime

import attr
from github.GithubException import GithubException
import pytz
from memoized import memoized
import os
import json
from commcare_cloud.fab.const import DATE_FMT
from commcare_cloud.alias import commcare_cloud
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
                    environment.new_release_name(),
                    environment.name),
                sha=diff.deploy_commit,
            )
        except GithubException as e:
            print(color_error(f"Error creating release tag: {e}"))


def record_deploy_start(environment, context):
    notify_slack_deploy_start(environment, context)
    send_deploy_start_email(environment, context)
    _log_deploy(environment, context)

def _log_deploy(environment, context, start_of_deploy=True):
    """
    Logs the deploy to a json file in the ~/.commcare-cloud directory. With start=True, a new deployment with the
    start_time will be recorded. With start=False, the latest deployment's end_time will be recorded.

    File contents example:
    {
        "<env>": {
            "<repo>": [
                {
                    "start_time": <start time>,
                    "end_time": <end time>,
                    "current_commit": <commit id>,
                    "deploy_commit": <commit id>
                }
            ]
        }
    }
    """
    commcare_cloud_path = os.path.expanduser("~/.commcare-cloud")
    if not os.path.exists(commcare_cloud_path):
        # We leave the creation of this folder to the init script
        return

    repo = context.diff.repo
    deploy_log_path = os.path.join(commcare_cloud_path, "deploy_log.json")
    deploy_log = {}
    if os.path.exists(deploy_log_path):
        with open(deploy_log_path, "r+") as file:
            deploy_log = json.loads(file.read())

    with open(deploy_log_path, "w") as file:
        if environment.name not in deploy_log:
            deploy_log[environment.name] = {}
        
        environment_repos = deploy_log[environment.name]
        if repo.name not in environment_repos:
            environment_repos[repo.name] = []
        
        repo_deploys = environment_repos[repo.name]
        format_time = lambda date_time: date_time.astimezone().strftime("%Y-%m-%dT%H:%M:%S %Z")

        if start_of_deploy:
            current_deploy = {
                'current_commit': context.diff.current_commit,
                'deploy_commit': context.diff.deploy_commit,
                'start_time': format_time(context.start_time),
                'end_time': None
                }
            repo_deploys.append(current_deploy)
        else:
            last_repo_deploy = repo_deploys[-1]
            last_repo_deploy['end_time'] = format_time(datetime.utcnow())
        json.dump(deploy_log, file)

def send_deploy_start_email(environment, context):
    is_nonstandard_deploy_time = not within_maintenance_window(environment)
    is_non_default_branch = (
        context.revision != environment.fab_settings_config.default_branch and
        context.revision is not None
    )
    env_name = environment.meta_config.deploy_env
    subject = f"{context.user} has initiated a {context.service_name} deploy to {env_name}"
    prefix = ""
    if is_nonstandard_deploy_time:
        subject += " outside maintenance window"
        prefix = "ATTENTION: "
    if is_non_default_branch:
        subject += f" with non-default branch '{context.revision}'"
        prefix = "ATTENTION: "
    subject = f"{prefix}{subject}"

    send_email(
        environment,
        subject=subject,
    )


def record_deploy_failed(environment, context):
    notify_slack_deploy_end(environment, context, is_success=False)
    send_email(
        environment,
        subject=f"{context.service_name} deploy to {environment.name} failed",
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
    _log_deploy(environment, context, start_of_deploy=False)


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
