import re

import jsonobject
from github.MainClass import Github
from memoized import memoized_property, memoized

from commcare_cloud.environment.exceptions import EnvironmentException
from commcare_cloud.environment.secrets.backends import all_secrets_backends_by_name
from commcare_cloud.environment.secrets.backends.abstract_backend import AbstractSecretsBackend
from commcare_cloud.fab.utils import get_github_credentials


@memoized
def get_github(repo):
    login_or_token, password = None, None
    if repo.is_private:
        message = "This environment references a private repository: {}".format(repo.url)
        login_or_token, password = get_github_credentials(message, force=True)
        if not login_or_token and not password:
            raise EnvironmentException("Github credentials required")
    return Github(login_or_token=login_or_token, password=password)


class GitRepository(jsonobject.JsonObject):
    name = jsonobject.StringProperty(required=True)
    url = jsonobject.StringProperty(required=True)
    dest = jsonobject.StringProperty(required=True)  # relative to the code_source/external directory
    version = jsonobject.StringProperty(default="master")
    requirements_path = jsonobject.StringProperty()
    deploy_key = jsonobject.StringProperty()  # name of the deploy key file to use
    is_private = jsonobject.BooleanProperty(default=False)

    @property
    def relative_dest(self):
        return "extensions/" + self.dest

    @memoized_property
    def repo(self):
        match = re.match(r"git@github.com:(.*?).git", self.url)
        if not match:
            raise EnvironmentException("Unable to parse repository URL: {}".format(self.url))
        repo = match.group(1)
        return get_github(self).get_repo(repo)

    @memoized
    def deploy_ref(self, code_branch):
        return self.repo.get_commit(code_branch or self.version).sha

    def to_generated_variables(self):
        vars = self.to_json()
        vars["dest"] = self.relative_dest
        return vars


class MetaConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    deploy_env = jsonobject.StringProperty(required=True)
    always_deploy_formplayer = jsonobject.BooleanProperty(default=False)
    env_monitoring_id = jsonobject.StringProperty(required=True)
    users = jsonobject.ListProperty(unicode, required=True)
    slack_alerts_channel = jsonobject.StringProperty()
    bare_non_cchq_environment = jsonobject.BooleanProperty(default=False)
    git_repositories = jsonobject.ListProperty(GitRepository)
    deploy_keys = jsonobject.DictProperty(unicode)
    secrets_backend = jsonobject.StringProperty(
        choices=all_secrets_backends_by_name.keys(),
        default='ansible-vault',
    )

    def get_secrets_backend_class(self):
        # guaranteed to succeed because of the validation above on secrets_backend
        return all_secrets_backends_by_name[self.secrets_backend]
