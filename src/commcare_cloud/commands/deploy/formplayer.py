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
from commcare_cloud.commands.deploy.utils import record_deploy_start, record_deploy_failed, \
    announce_deploy_success, create_release_tag, DeployContext
from commcare_cloud.user_utils import get_default_username
from commcare_cloud.commands.utils import timeago
from commcare_cloud.events import publish_deploy_event
from commcare_cloud.fab.deploy_diff import DeployDiff
from commcare_cloud.github import github_repo

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

    tag_commits = environment.fab_settings_config.tag_deploy_commits
    repo = github_repo('dimagi/formplayer', require_write_permissions=tag_commits)

    diff = get_deploy_diff(environment, repo)
    diff.print_deployer_diff()

    context = DeployContext(
        service_name="Formplayer",
        revision=args.commcare_rev,
        diff=diff,
        start_time=datetime.utcnow()
    )

    if not ask('Continue with deploy?', quiet=args.quiet):
        return 1

    record_deploy_start(environment, context)

    rc = run_ansible_playbook_command(environment, args)
    if rc != 0:
        record_deploy_failed(environment, context.service_name)
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
        record_deploy_failed(environment, context.service_name)
        return rc

    record_deploy_success(environment, context)
    return 0


def record_deploy_success(environment, context):
    end = datetime.utcnow()
    diff = context.diff
    repo = diff.repo
    create_release_tag(environment, repo, diff)
    record_deploy_in_datadog(environment, diff, end - context.start_time)
    update_sentry_post_deploy(environment, "formplayer", repo, diff, context.start_time, end)
    announce_deploy_success(environment, context)
    publish_deploy_event("deploy_success", "formplayer", environment)


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
        new_version_details=new_version_details,
        generate_diff=environment.fab_settings_config.generate_deploy_diffs
    )
    return diff


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


def record_deploy_in_datadog(environment, diff, tdelta):
    if environment.public_vars.get('DATADOG_ENABLED', False):
        print(color_summary(f">> Recording deploy in Datadog"))
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
