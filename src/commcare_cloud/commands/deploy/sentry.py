import requests
from jsonobject.base import namedtuple


def update_sentry_post_deploy(environment, diff, deploy_start, deploy_end):
    localsettings = environment.public_vars["localsettings"]
    client = SentryClient(
        environment.get_secret('SENTRY_API_KEY'),
        localsettings.get("SENTRY_REPOSITORY"),
        localsettings.get('SENTRY_ORGANIZATION_SLUG'),
        localsettings.get('SENTRY_PROJECT_SLUG'),
    )
    if client.is_valid():
        release_name = environment.new_release_name()
        client.create_release(release_name, diff.deploy_commit)
        client.create_deploy(
            release_name, environment.meta_config.env_monitoring_id,
            deploy_start, deploy_end
        )


class SentryClient(namedtuple("SentryClient", "api_key, repo_name, org_slug, project_slug")):
    def is_valid(self):
        return all(self)

    def create_release(self, release_name, git_commit):
        # TODO: include more commit detail: https://docs.sentry.io/product/releases/setup/manual-setup-releases/
        payload = {
            'version': release_name,
            'refs': [{
                'repository': self.repo_name,
                'commit': git_commit
            }],
            'projects': [self.project_slug]
        }

        headers = {'Authorization': 'Bearer {}'.format(self.api_key), }
        releases_url = f"https://sentry.io/api/0/organizations/{self.org_slug}/releases/"
        response = requests.post(releases_url, headers=headers, json=payload)
        if response.status_code == 208:
            # already created so update
            payload.pop('version')
            requests.put('{}{}/'.format(releases_url, release_name), headers=headers, json=payload)

    def create_deploy(self, release_name, env_name, deploy_start, deploy_end):
        payload = {
            'environment': env_name,
            'dateStarted': f"{deploy_start.isoformat()}Z",
            'dateFinished': f"{deploy_end.isoformat()}Z",
        }

        headers = {'Authorization': 'Bearer {}'.format(self.api_key), }
        releases_url = f'https://sentry.io/api/0/organizations/{self.org_slug}/releases/{release_name}/deploys/'
        requests.post(releases_url, headers=headers, json=payload)
