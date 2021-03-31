from collections import namedtuple
from datetime import datetime

import requests
from clint.textui import indent

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_warning
from commcare_cloud.commands.ansible import ansible_playbook
from commcare_cloud.commands.ansible.helpers import AnsibleContext
from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.fab.git_repo import get_github
from commcare_cloud.fab.deploy_diff import DeployDiff

GIT_PROPERTIES = "https://s3.amazonaws.com/dimagi-formplayer-jars/latest-successful/git.properties"
BUILD_INFO_PROPERTIES = "https://s3.amazonaws.com/dimagi-formplayer-jars/latest-successful/build-info.properties"


class VersionInfo(namedtuple("VersionInfo", "commit, message, time, build_time")):
    @property
    def build_time_ago(self):
        build_time = datetime.strptime(self.build_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        return datetime.utcnow() - build_time


def deploy_formplayer(environment, args):
    current_commit = get_current_formplayer_version(environment)
    latest_version = get_latest_formplayer_version()

    if latest_version:
        print("Preparing to deploy formplayer:")
        with indent():
            print(f"Commit          : {latest_version.commit}")
            print(f"Commit message  : {latest_version.message}")
            print(f"Commit date     : {latest_version.time}")
            print(f"Build time      : {latest_version.build_time} ({latest_version.build_time_ago} ago)")

        if not current_commit:
            print(color_warning("Unable to get deployed version for generating a deploy diff."))
        else:
            repo = get_github().get_repo('dimagi/formplayer')
            diff = DeployDiff(repo, latest_version.commit, current_commit)
            diff.print_deployer_diff()
    else:
        print(color_warning("Unable to get version info."))

    if not ask('Continue with deploy?', quiet=args.quiet):
        return 1

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


def get_current_formplayer_version(environment):
    formplayer0 = environment.groups["formplayer"][0]
    res = requests.get(f"http://{formplayer0}:8081/info")
    res.raise_for_status()
    info = res.json()
    return info.get("git", {}).get("commit", {}).get("id", None)


def get_latest_formplayer_version():
    def get_url_content(url):
        res = requests.get(url)
        res.raise_for_status()
        return res.text

    def extract_vals_from_property_data(data, mapping):
        out = {}
        for line in data.splitlines(keepends=False):
            key, value = line.split("=")
            if key in mapping:
                out[mapping[key]] = value.replace("\\", "")
        return out

    git_info = get_url_content(GIT_PROPERTIES)
    build_info = get_url_content(BUILD_INFO_PROPERTIES)
    git_data = extract_vals_from_property_data(git_info, {
        "git.commit.id": "commit",
        "git.commit.message.short": "message",
        "git.commit.time": "time"
    })
    build_data = extract_vals_from_property_data(build_info, {"build.time": "build_time"})
    return VersionInfo(**git_data, **build_data)
