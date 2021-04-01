from collections import namedtuple
from datetime import datetime

import pytz
import requests
from dateutil import parser
from requests import RequestException

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_warning, color_notice, color_summary
from commcare_cloud.commands.ansible import ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.deploy.sentry import update_sentry_post_deploy
from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.commands.utils import timeago
from commcare_cloud.fab.deploy_diff import DeployDiff
from commcare_cloud.fab.git_repo import get_github, github_auth_provided

AWS_BASE_URL_ENV = {
    "staging": "https://s3.amazonaws.com/dimagi-formplayer-jars/staging/latest-successful"
}
AWS_BASE_URL_DEFAULT = "https://s3.amazonaws.com/dimagi-formplayer-jars/latest-successful"
GIT_PROPERTIES = "git.properties"
BUILD_INFO_PROPERTIES = "build-info.properties"


class VersionInfo(namedtuple("VersionInfo", "commit, message, time, build_time")):
    @property
    def commit_time_ago(self):
        return self._format_time_ago(self.time)

    @property
    def build_time_ago(self):
        return self._format_time_ago(self.build_time)

    @staticmethod
    def _format_time_ago(time):
        build_time = parser.parse(time)
        if build_time.tzinfo:
            build_time = build_time.astimezone(pytz.utc).replace(tzinfo=None)
        delta = datetime.utcnow() - build_time
        return timeago(delta)


def deploy_formplayer(environment, args):
    print(color_notice("\nPreparing to deploy Formplayer to: "), end="")
    print(f"{environment.name}\n")

    # do this first to get the git prompt out the way
    repo = get_github().get_repo('dimagi/formplayer') if github_auth_provided() else None

    diff = get_deploy_diff(environment, repo)
    diff.print_deployer_diff()

    if not ask('Continue with deploy?', quiet=args.quiet):
        return 1

    start = datetime.utcnow()
    announce_formplayer_deploy_start(environment)

    rc = run_ansible_playbook_command(environment, args)
    if rc != 0:
        announce_deploy_failed(environment)
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
        announce_deploy_failed(environment)
        return rc

    record_deploy_success(environment, repo, diff, start)


def record_deploy_success(environment, repo, diff, start):
    end = datetime.utcnow()
    create_release_tag(environment, repo, diff)
    record_deploy_in_datadog(environment, diff, end - start)
    update_sentry_post_deploy(environment, diff, start, end)
    announce_deploy_success(environment, diff.get_email_diff())


def get_deploy_diff(environment, repo):
    print(color_summary(">> Compiling deploy summary"))

    current_commit = get_current_formplayer_version(environment)
    latest_version = get_latest_formplayer_version(environment.name)
    new_version_details = {}
    if latest_version:
        new_version_details["Release Name"] = environment.new_release_name()
        new_version_details["Commit"] = latest_version.commit
        new_version_details["Commit message"] = latest_version.message
        new_version_details["Commit date"] = f"{latest_version.commit_time_ago} ({latest_version.time})"
        new_version_details["Build time"] = f"{latest_version.build_time_ago} ({latest_version.build_time})"
    diff = DeployDiff(
        repo, current_commit, latest_version.commit,
        new_version_details=new_version_details
    )
    return diff


def create_release_tag(environment, repo, diff):
    if not github_auth_provided() or not environment.fab_settings_config.tag_deploy_commits:
        return
    repo.create_git_ref(
        ref='refs/tags/{}-{}-release'.format(
            environment.new_release_name(),
            environment.name),
        sha=diff.deploy_commit,
    )


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
        subject="{user} has initiated a Formplayer deploy to {environment}".format(
            user=get_default_username(),
            environment=environment.meta_config.deploy_env,
        ),
    )


def announce_deploy_failed(environment):
    mail_admins(
        environment,
        subject=f"Formplayer deploy to {environment.name} failed",
    )


def announce_deploy_success(environment, diff_ouptut):
    mail_admins(
        environment,
        subject=f"Formplayer deploy successful - {environment.name}",
        message=diff_ouptut
    )


def mail_admins(environment, subject, message=''):
    print(color_summary(f">> Sending email: {subject}"))
    if environment.fab_settings_config.email_enabled:
        commcare_cloud(
            environment.name, 'django-manage', '--quiet', 'mail_admins',
            '--subject', subject,
            '--environment', environment.meta_config.deploy_env,
            '--html',
            message,
            show_command=False
        )


def record_deploy_in_datadog(environment, diff, tdelta):
    if environment.public_vars.get('DATADOG_ENABLED', False):
        print(color_summary(f">> Recording deploy in Datadog"))
        diff_url = ""
        if github_auth_provided():
            diff_url = f"\nDiff link: [Git Diff]({diff.url})"
        deploy_notification_text = (
            "Formplayer has been successfully deployed to "
            "*{}* by *{}* in *{}* minutes.\nRelease Name: {}{}".format(
                environment.name,
                get_default_username(),
                int(tdelta.total_seconds() / 60) or '?',
                environment.new_release_name(),
                diff_url
            )
        )
        commcare_cloud(
            environment.name, 'send-datadog-event',
            'Formplayer Deploy Success',
            deploy_notification_text,
            '--alert_type', "success",
            show_command=False
        )

def get_current_formplayer_version(environment):
    """Get version of currently deployed Formplayer by querying
    the Formplayer management endpoint to get the build info.
    """
    formplayer0 = environment.groups["formplayer"][0]
    try:
        res = requests.get(f"http://{formplayer0}:8081/info", timeout=5)
        res.raise_for_status()
    except RequestException as e:
        print(color_warning(f"Error getting current formplayer version: {e}"))
        return

    info = res.json()
    return info.get("git", {}).get("commit", {}).get("id", None)


def get_latest_formplayer_version(env_name):
    """Get version info of latest available version. This fetches
    meta files from S3 and parses them to get the data.
    """
    def get_url_content(url):
        res = requests.get(url)
        res.raise_for_status()
        return res.text

    def extract_vals_from_property_data(data, mapping):
        out = {}
        for line in data.splitlines(keepends=False):
            if not line.strip():
                continue
            key, value = line.strip().split("=")
            if key in mapping:
                out[mapping[key]] = strip_escapes(value)
        return out

    git_info_url, build_info_url = get_info_urls(env_name)
    try:
        git_info = get_url_content(git_info_url)
        build_info = get_url_content(build_info_url)
    except RequestException as e:
        print(color_warning(f"Error getting latest formplayer version: {e}"))
        return

    git_data = extract_vals_from_property_data(git_info, {
        "git.commit.id": "commit",
        "git.commit.message.short": "message",
        "git.commit.time": "time"
    })
    build_data = extract_vals_from_property_data(build_info, {"build.time": "build_time"})
    return VersionInfo(**git_data, **build_data)


def strip_escapes(value):
    return value.replace("\\", "")


def get_info_urls(env_name):
    """
    :return: tuple(git_info_url, build_info_url)
    """
    base_url = AWS_BASE_URL_ENV.get(env_name, AWS_BASE_URL_DEFAULT)
    return f"{base_url}/{GIT_PROPERTIES}", f"{base_url}/{BUILD_INFO_PROPERTIES}"
