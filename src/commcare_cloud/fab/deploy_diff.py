import os
import re
from collections import defaultdict

import jinja2
from gevent.pool import Pool
from memoized import memoized

from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.fab.git_repo import github_auth_provided

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'diff_templates')
LABELS_TO_EXPAND = [
    "product/all-users-all-environments",
    "product/prod-india-all-users",
    "product/feature-flag",
    "product/all-users",
]


class DeployDiff:
    def __init__(self, repo, current_commit, deploy_commit, new_version_details=None):
        """
        :param repo: github.Repository.Repository object
        :param current_commit: Commit SHA of the currently deployed code
        :param deploy_commit: Commit SHA of the code being deployed
        :param new_version_details: dict of additional metadata to display in diff output.
        """
        self.repo = repo
        self.current_commit = current_commit
        self.deploy_commit = deploy_commit
        self.new_version_details = new_version_details
        self.j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))
        register_console_filters(self.j2)

    @property
    def url(self):
        """Human-readable diff URL"""
        return "{}/compare/{}...{}".format(self.repo.html_url, self.current_commit, self.deploy_commit)

    @property
    def deployed_commit_matches_latest_commit(self):
        if self.current_commit and self.deploy_commit:
            short, long = sorted([self.current_commit, self.deploy_commit], key=lambda x: len(x))
            return self.current_commit == self.deploy_commit or long.startswith(short)
        return False

    @memoized
    def get_diff_context(self):
        context = {
            "new_version_details": self.new_version_details,
            "user": get_default_username(),
            "LABELS_TO_EXPAND": LABELS_TO_EXPAND,
            "errors": [],
            "warnings": []
        }

        if self.deployed_commit_matches_latest_commit:
            context["errors"].append("Versions are identical. No changes since last deploy.")
            return context

        if not (github_auth_provided() and self.current_commit and self.deploy_commit):
            context["warnings"].append("Insufficient info to get deploy diff.")
            return context

        context["compare_url"] = self.url
        pr_numbers = self._get_pr_numbers()
        if len(pr_numbers) > 500:
            context["warnings"].append("There are too many PRs to display")
            return context
        elif not pr_numbers:
            context["warnings"].append("No PRs merged since last release.")
            return context

        pool = Pool(5)
        pr_infos = [_f for _f in pool.map(self._get_pr_info, pr_numbers) if _f]

        context["pr_infos"] = pr_infos
        prs_by_label = self._get_prs_by_label(pr_infos)
        context["prs_by_label"] = prs_by_label
        return context

    def print_deployer_diff(self):
        print(self.render_diff('console.txt.j2'))

    def get_email_diff(self):
        return self.render_diff("email.html.j2")

    def render_diff(self, template_name):
        template = self.j2.get_template(template_name)
        return template.render(
            **self.get_diff_context()
        )

    def _get_pr_numbers(self):
        comparison = self.repo.compare(self.current_commit, self.deploy_commit)
        return [
            int(re.search(r'Merge pull request #(\d+)',
                          repo_commit.commit.message).group(1))
            for repo_commit in comparison.commits
            if repo_commit.commit.message.startswith('Merge pull request')
        ]

    def _get_pr_info(self, pr_number):
        pr_response = self.repo.get_pull(pr_number)
        if not pr_response.number:
            # Likely rate limited by Github API
            return None
        assert pr_number == pr_response.number, (pr_number, pr_response.number)

        return {
            'number': pr_response.number,
            'title': pr_response.title,
            'url': pr_response.html_url,
            'labels': pr_response.labels,
            'additions': pr_response.additions,
            'deletions': pr_response.deletions,
            'opened_by': pr_response.user.login,
            'body': pr_response.body,
        }

    def _get_prs_by_label(self, pr_infos):
        prs_by_label = defaultdict(list)
        for pr in pr_infos:
            for label in pr['labels']:
                prs_by_label[label.name].append(pr)
        return dict(prs_by_label)


def register_console_filters(env):
    from fabric.colors import red, blue, cyan, yellow, green, magenta

    filters = {
        "error": red,
        "success": green,
        "highlight": yellow,
        "summary": blue,
        "warning": magenta,
        "code": cyan,
    }

    for name, filter_ in filters.items():
        env.filters[name] = filter_
