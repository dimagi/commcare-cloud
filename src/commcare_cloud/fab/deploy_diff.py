import re
from collections import defaultdict

from gevent.pool import Pool
from memoized import memoized

from commcare_cloud.fab.git_repo import _github_auth_provided


LABELS_TO_EXPAND = [
    "reindex/migration",
]


class DeployDiff:
    def __init__(self, repo, last_commit, deploy_commit, output=None):
        self.repo = repo
        self.last_commit = last_commit
        self.deploy_commit = deploy_commit
        self.output = output or Output()

    @property
    def url(self):
        """Human-readable diff URL"""
        return "{}/compare/{}...{}".format(self.repo.html_url, self.last_commit, self.deploy_commit)

    @memoized
    def get_diff_output(self):
        if not (_github_auth_provided() and self.last_commit and self.deploy_commit):
            return self.output

        short, long = sorted([self.last_commit, self.deploy_commit], key=lambda x: len(x))
        if (self.last_commit == self.deploy_commit or (
            long.startswith(short)
        )):
            self.output("Versions are identical. No changes since last deploy.", Output.ERROR)
            return self.output

        pr_numbers = self._get_pr_numbers()
        if len(pr_numbers) > 500:
            self.output("There are too many PRs to display", Output.ERROR)
            return self.output
        elif not pr_numbers:
            self.output("No PRs merged since last release.", Output.SUMMARY)
            self.output(f"\tView full diff here: {self.url}")
            return self.output

        pool = Pool(5)
        pr_infos = [_f for _f in pool.map(self._get_pr_info, pr_numbers) if _f]

        self.output("\nList of PRs since last deploy:", Output.SUMMARY)
        self._append_prs_formatted(pr_infos)

        prs_by_label = self._get_prs_by_label(pr_infos)
        if prs_by_label.get('reindex/migration'):
            self.output('You are about to deploy the following PR(s), which will trigger a '
                               'reindex or migration. Click the URL for additional context.', Output.ERROR)
            self._append_prs_formatted(prs_by_label['reindex/migration'])

        return self.output

    def print_deployer_diff(self):
        print(self.get_diff_output().console_output())

    def _get_pr_numbers(self):
        comparison = self.repo.compare(self.last_commit, self.deploy_commit)
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

        labels = [label.name for label in pr_response.labels]

        return {
            'number': pr_response.number,
            'title': pr_response.title,
            'url': pr_response.html_url,
            'labels': labels,
            'additions': pr_response.additions,
            'deletions': pr_response.deletions,
        }

    def _get_prs_by_label(self, pr_infos):
        prs_by_label = defaultdict(list)
        for pr in pr_infos:
            for label in pr['labels']:
                prs_by_label[label].append(pr)
        return dict(prs_by_label)

    def _append_prs_formatted(self, pr_list):
        for pr in pr_list:
            self.output("- ", end="")
            self.output(pr['title'], formatting=Output.CODE, end=": ")
            self.output(pr['url'], formatting=Output.HIGHLIGHT, end=" ")
            self.output("({})".format(", ".join(label for label in pr['labels'])))


class Output:
    ERROR = "error"
    SUCCESS = "success"
    HIGHLIGHT = "highlight"
    SUMMARY = "summary"
    WARNING = "warning"
    CODE = "code"

    def __init__(self):
        self._lines = []

    def __call__(self, value, formatting=None, end="\n"):
        self._lines.append((f"{value}{end}", formatting))

    def console_output(self):
        return "".join([
            self._console_format(value, formatting) for value, formatting in self._lines
        ])

    def plain_output(self):
        return "".join([
            value for value, _ in self._lines
        ])

    def _console_format(self, value, formatting):
        from fabric.colors import red, blue, cyan, yellow, green, magenta, white
        formatters = {
            Output.ERROR: red,
            Output.SUCCESS: green,
            Output.HIGHLIGHT: yellow,
            Output.SUMMARY: blue,
            Output.WARNING: magenta,
            Output.CODE: cyan,
        }
        return formatters[formatting](value) if formatting else value
