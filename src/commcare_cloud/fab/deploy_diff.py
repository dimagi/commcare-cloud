import os
import re
from collections import defaultdict

import jinja2
from gevent.pool import Pool
from github.GithubException import GithubException
from memoized import memoized, memoized_property

from commcare_cloud.colors import (
    color_warning, color_error, color_success,
    color_highlight, color_summary, color_code
)
from commcare_cloud.user_utils import get_default_username

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'diff_templates')
LABELS_TO_EXPAND = [
    "product/all-users-all-environments",
    "product/prod-india-all-users",
    "product/feature-flag",
    "product/all-users",
]


class DeployDiff:
    def __init__(self, repo, current_commit, deploy_commit, new_version_details=None, generate_diff=True):
        """
        :param repo: github.Repository.Repository object
        :param current_commit: Commit SHA of the currently deployed code
        :param deploy_commit: Commit SHA of the code being deployed
        :param new_version_details: dict of additional metadata to display in diff output.
        :param generate_diff: True if deploy diffs should be produced
        """
        self.repo = repo
        self.current_commit = current_commit
        self.deploy_commit = deploy_commit
        self.new_version_details = new_version_details
        self.generate_diff = generate_diff
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

        if not (self.current_commit and self.deploy_commit):
            context["warnings"].append("Insufficient info to get deploy diff.")
            return context

        context["compare_url"] = self.url

        if not self.generate_diff:
            disabled_msg = "Deploy diffs disabled for this environment."
            print(color_warning(disabled_msg))
            context["warnings"].append(disabled_msg)
            return context

        if not self.repo.permissions:
            # using unauthenticated API calls, skip diff creation to avoid hitting rate limits
            print(color_warning("Diff generation skipped. Supply a Github token to see deploy diffs."))
            context["warnings"].append("Diff omitted.")
            return context

        try:
            pr_numbers = self._get_pr_numbers()
        except GithubException as e:
            print(color_error(f"Error getting diff commits: {e}"))
            context["warnings"].append("There was an error fetching the PRs since the last deploy.")
            return context

        if len(pr_numbers) > 500:
            context["warnings"].append("There are too many PRs to display.")
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

    @memoized_property
    def git_comparison(self):
        return self.repo.compare(self.current_commit, self.deploy_commit)

    def _get_pr_numbers(self):
        comparison = self.git_comparison
        return [
            int(re.search(r'Merge pull request #(\d+)',
                          repo_commit.commit.message).group(1))
            for repo_commit in comparison.commits
            if repo_commit.commit.message.startswith('Merge pull request')
        ]

    def _get_pr_info(self, pr_number):
        try:
            pr_response = self.repo.get_pull(pr_number)
        except GithubException as e:
            print(color_error(f"Error getting PR details for {pr_number}: {e}"))
            return None

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
    filters = {
        "error": color_error,
        "success": color_success,
        "highlight": color_highlight,
        "summary": color_summary,
        "warning": color_warning,
        "code": color_code,
    }

    for name, filter_ in filters.items():
        env.filters[name] = filter_
