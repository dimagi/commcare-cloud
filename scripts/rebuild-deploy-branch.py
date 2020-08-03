#!/usr/bin/env python
"""
This file is meant to be used in the following manner:

$ python rebuild-deploy-branch.py icds-staging [-v] [--no-push] [fetch] [sync] [rebuild]

Where deploy_branches.yaml looks as follows:

    trunk: master
    name: autostaging
    branches:
      - feature1
      - feature2
      - forkowner:feature3 # branch from fork of repository
    submodules:
      submodules/module1:
        branches:
          - feature1
          - forkowner:feature2 # branch from fork of repository
      submodules/module2:
        trunk: develop
        branches:
          - feature2

Multile repositories can also be specified:

   dimagi/commcare-hq:  # this repo is required
     trunk: master
     ...

   another/repo:
     trunk: master
     ...

When not specified, a submodule's trunk and name inherit from the parent
"""
from __future__ import print_function
from gevent import monkey
monkey.patch_all()

import os
import re
from contextlib2 import ExitStack

import gevent
import jsonobject
import sh

from gitutils import (
    OriginalBranch,
    get_git,
    git_recent_tags,
    has_merge_conflict,
    print_merge_details,
)
from sh_verbose import ShVerbose


class BranchConfig(jsonobject.JsonObject):
    trunk = jsonobject.StringProperty()
    name = jsonobject.StringProperty()
    branches = jsonobject.ListProperty(str)
    submodules = jsonobject.DictProperty(lambda: BranchConfig)
    pull_requests = jsonobject.ListProperty(str)

    def normalize(self):
        for submodule, subconfig in self.submodules.items():
            subconfig.trunk = subconfig.trunk or self.trunk
            subconfig.name = subconfig.name or self.name
            subconfig.normalize()

    def span_configs(self, path=('.',)):
        for submodule, subconfig in self.submodules.items():
            for item in subconfig.span_configs(path + (submodule,)):
                yield item
        yield os.path.join(*path), self

    def check_trunk_is_recent(self, path=None):
        # if it doesn't match our tag format
        if re.match(r'[\d-]+_[\d\.]+-\w+-deploy', self.trunk) is None:
            return True

        return self.trunk in git_recent_tags(path)


def fetch_remote(base_config, name="origin"):
    jobs = []
    seen = set()
    fetched = set()
    for path, config in base_config.span_configs((base_config.root,)):
        if path in seen:
            continue
        seen.add(path)
        git = get_git(path)
        remotes = set(git.remote().split())
        print("  [{cwd}] fetching {name}".format(cwd=path, name=name))
        jobs.append(gevent.spawn(git.fetch, name))
        for branch in (b for b in config.branches if ":" in b):
            remote, branch = branch.split(":", 1)
            if remote not in remotes:
                url = remote_url(git, remote)
                print("  [{path}] adding remote: {remote} -> {url}"
                      .format(**locals()))
                git.remote("add", remote, url)
                remotes.add(remote)
            print("  [{path}] fetching {remote} {branch}".format(**locals()))
            jobs.append(gevent.spawn(git.fetch, remote, branch))
            fetched.add(remote)

        for pr in config.pull_requests:
            print("  [{path}] fetching pull request {pr}".format(**locals()))
            pr = 'pull/{pr}/head:enterprise-{pr}'.format(pr=pr)
            jobs.append(gevent.spawn(git.fetch, 'origin', pr))

    gevent.joinall(jobs)
    print("fetched {}".format(", ".join(['origin'] + sorted(fetched))))


def remote_url(git, remote, original="origin"):
    origin_url = sh.grep(git.remote("-v"), original).split()[1]
    repo_name = origin_url.rsplit("/", 1)[1]
    return "https://github.com/{}/{}".format(remote, repo_name)


def has_ref(git, ref):
    """Return true if the named branch exists"""
    try:
        out = git("show-ref", "--verify", "--quiet", ref)
    except sh.ErrorReturnCode:
        return False
    return out.exit_code == 0


def has_local(git, branch):
    """Return true if the named local branch exists"""
    return has_ref(git, "refs/heads/{}".format(branch))


def has_remote(git, ref):
    """Return true if the named remote branch exists

    :param ref: Remote ref (example: origin/branch-name)
    """
    return has_ref(git, "refs/remotes/{}".format(ref))


def origin(branch):
    return "origin/{}".format(branch)


def sync_local_copies(config, push=True):
    base_config = config
    unpushed_branches = []

    def _count_commits(compare_spec):
        return int(sh.wc(git.log(compare_spec, '--oneline', _piped=True), '-l'))

    for path, config in base_config.span_configs((base_config.root,)):
        git = get_git(path)
        with OriginalBranch(git):
            for branch in [config.trunk] + config.branches:
                if ":" in branch or not has_local(git, branch):
                    continue
                git.checkout(branch)
                unpushed = _count_commits('origin/{0}..{0}'.format(branch))
                unpulled = _count_commits('{0}..origin/{0}'.format(branch))
                if unpulled or unpushed:
                    print(("  [{cwd}] {branch}: {unpushed} ahead "
                           "and {unpulled} behind origin").format(
                        cwd=path,
                        branch=branch,
                        unpushed=unpushed,
                        unpulled=unpulled,
                    ))
                else:
                    print("  [{cwd}] {branch}: Everything up-to-date.".format(
                        cwd=path,
                        branch=branch,
                    ))
                if unpushed:
                    unpushed_branches.append((path, branch))
                elif unpulled:
                    print("  Fastforwarding your branch to origin")
                    git.merge('--ff-only', origin(branch))
    if unpushed_branches and push:
        print("The following branches have commits that need to be pushed:")
        for path, branch in unpushed_branches:
            print("  [{cwd}] {branch}".format(cwd=path, branch=branch))
        exit(1)
    else:
        print("All branches up-to-date.")


def rebuild_staging(config, print_details=True, push=True):
    merge_conflicts = []
    not_found = []
    all_configs = list(config.span_configs((config.root,)))
    with ExitStack() as stack:
        for path, _ in all_configs:
            stack.enter_context(OriginalBranch(get_git(path)))
        for path, config in all_configs:
            git = get_git(path)
            try:
                git.checkout('-B', config.name, origin(config.trunk), '--no-track')
            except Exception:
                git.checkout('-B', config.name, config.trunk, '--no-track')
            for branch in config.branches:
                remote = ":" in branch
                if remote or not has_local(git, branch):
                    if remote:
                        remote_branch = branch.replace(":", "/", 1)
                    else:
                        remote_branch = origin(branch)
                    if not has_remote(git, remote_branch):
                        not_found.append((path, branch))
                        print("  [{cwd}] {branch} NOT FOUND".format(
                            cwd=format_cwd(path),
                            branch=branch,
                        ))
                        continue
                    branch = remote_branch
                print("  [{cwd}] Merging {branch} into {name}".format(
                    cwd=path,
                    branch=branch,
                    name=config.name
                ), end=' ')
                try:
                    git.merge(branch, '--no-edit')
                except sh.ErrorReturnCode_1:
                    merge_conflicts.append((path, branch, config))
                    try:
                        git.merge("--abort")
                    except sh.ErrorReturnCode_128:
                        pass
                    print("FAIL")
                else:
                    print("ok")
            for pr in config.pull_requests:
                branch = "enterprise-{pr}".format(pr=pr)
                print("  [{cwd}] Merging {pr} into {name}".format(
                    cwd=path,
                    pr=pr,
                    name=config.name
                ), end=' ')
                try:
                    git.merge(branch, '--no-edit')
                except sh.ErrorReturnCode_1:
                    merge_conflicts.append((path, branch, config))
                    try:
                        git.merge("--abort")
                    except sh.ErrorReturnCode_128:
                        pass
                    print("FAIL")
                else:
                    print("ok")
            if config.submodules:
                for submodule in config.submodules:
                    git.add(submodule)
                git.commit('-m', "update submodule refs", '--no-edit',
                           '--allow-empty')
        if push and not (merge_conflicts or not_found):
            for path, config in all_configs:
                # stupid safety check
                assert config.name != 'master', path
                print("  [{cwd}] Force pushing to origin {name}".format(
                    cwd=path,
                    name=config.name,
                ))
                force_push(get_git(path), config.name)

    if not_found:
        print("You must remove the following branches before rebuilding:")
        for cwd, branch in not_found:
            print("  [{cwd}] {branch}".format(
                cwd=format_cwd(cwd),
                branch=branch,
            ))
    if merge_conflicts:
        print("You must fix the following merge conflicts before rebuilding:")
        for cwd, branch, config in merge_conflicts:
            print("\n[{cwd}] {branch} => {name}".format(
                cwd=format_cwd(cwd),
                branch=branch,
                name=config.name,
            ))
            git = get_git(cwd)
            if print_details:
                print_conflicts(branch, config, git)

    if merge_conflicts or not_found:
        exit(1)


def print_conflicts(branch, config, git):
    if has_merge_conflict(branch, config.trunk, git):
        print(red("{} conflicts with {}".format(branch, config.trunk)))
        return

    conflict_found = False
    for other_branch in config.branches:
        if has_merge_conflict(branch, other_branch, git):
            print(red("{} conflicts with {}".format(branch, other_branch)))
            conflict_found = True

    if not conflict_found:
        print_merge_details(branch, config.name, git,
                            known_branches=config.branches)


def force_push(git, branch):
    try:
        git.push('origin', branch, '--force')
    except sh.ErrorReturnCode_128 as e:
        # oops we're using a read-only URL, so change to the suggested url
        try:
            line = sh.grep(git.remote("-v"),
                           '-E', r'^origin.(https|git)://github\.com/.*\(push\)$')
        except sh.ErrorReturnCode_1:
            raise e
        old_url = line.strip().split()[1]
        prefix = "git" if old_url.startswith("git:") else "https"
        new_url = old_url.replace(prefix + "://github.com/", "git@github.com:")
        print("    {} -> {}".format(old_url, new_url))
        git.remote('set-url', 'origin', new_url)
        git.push('origin', branch, '--force')


def format_cwd(cwd):
    return os.path.join(cwd) if cwd else '.'


class DisableGitHooks(object):
    already_disabled = None

    def __init__(self, path='.git/hooks'):
        import uuid
        self.path = path
        self.guid = uuid.uuid4().hex

    @property
    def hidden_path(self):
        return self.path + '-' + self.guid

    def __enter__(self):
        try:
            sh.test('-d', self.path)
            self.already_disabled = False
        except sh.ErrorReturnCode_1:
            self.already_disabled = True
        else:
            sh.mv(self.path, self.hidden_path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.already_disabled:
            sh.mv(self.hidden_path, self.path)


def _wrap_with(code):

    def inner(text, bold=False):
        c = code

        if bold:
            c = "1;%s" % c
        return "\033[%sm%s\033[0m" % (c, text)
    return inner


red = _wrap_with('31')


def main():
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description='Rebuild the deploy branch for an environment')
    parser.add_argument("env", help="Name of the environment")
    parser.add_argument("actions", nargs="*")
    parser.add_argument("--commcare-hq-root", help="Path to cloned commcare-hq repository",
                        default=os.environ.get("COMMCARE_HQ_ROOT"))
    parser.add_argument("-v", "--verbose")
    parser.add_argument("--no-push", action="store_true", help="Do not push the changes to remote git repository.")
    args = parser.parse_args()

    if not args.commcare_hq_root:
        print(red(
            "Path to commcare-hq repository must be provided.\n"
            "Use '--commcare-hq-root=[path]' or set the 'COMMCARE_HQ_ROOT' environment variable."
        ))
        exit(1)

    config_path = os.path.join("environments", args.env, "deploy_branches.yml")

    git = get_git()
    print("Fetching master")
    git.fetch("origin", "master")
    if not args.no_push:
        print("Checking branch config for modifications")
        if git.diff("origin/master", "--", config_path):
            print(red("'{}' on this branch different from the one on master".format(config_path)))
    exit(0)

    with open(config_path) as config_yaml:
        config = yaml.safe_load(config_yaml)

    if "trunk" in config:
        config = BranchConfig.wrap(config)
        config.normalize()
        repositories = {"dimagi/commcare-hq": config}
    elif "dimagi/commcare-hq" in config:
        repositories = {
            repo: BranchConfig.wrap(repo_config)
            for repo, repo_config in config.items()
        }
        for repo, repo_config in repositories.items():
            repo_config.normalize()
            if repo == "dimagi/commcare-hq":
                repo_config.root = os.path.abspath(args.commcare_hq_root)
            else:
                env_var = "{}_ROOT".format(re.sub("[/-]", "_", repo).upper())
                code_root = os.environ.get(env_var)
                if not code_root:
                    code_root = raw_input("Please supply the location of the '{}' repo: ".format(repo))

                if not code_root or not os.path.exists(code_root):
                    print(red(
                        "Repo path must be supplied. "
                        "Consider setting the '{}' environment variable".format(env_var)
                    ))
                    exit(1)
                repo_config.root = os.path.abspath(code_root)
    else:
        print(red("Unexpected format for config file."))
        exit(1)

    for config in repositories.values():
        if not config.check_trunk_is_recent(config.root):
            print("The trunk is not based on a very recent commit")
            print("Consider using one of the following:")
            print(git_recent_tags(config.root))
            exit(1)
    if not args.actions:
        args.actions = 'fetch sync rebuild'.split()
    push = not args.no_push
    with DisableGitHooks(), ShVerbose(args.verbose):
        for repo, config in repositories.items():
            print("\nRebuilding '{}' branch in '{}' repo.".format(config.name, repo))
            if 'fetch' in args.actions:
                fetch_remote(config)
            if 'sync' in args.actions:
                sync_local_copies(config, push=push)
            if 'rebuild' in args.actions:
                rebuild_staging(config, push=push)


if __name__ == '__main__':
    main()
