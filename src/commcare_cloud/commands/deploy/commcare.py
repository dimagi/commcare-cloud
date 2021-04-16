from datetime import datetime

from clint.textui import indent

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_summary
from commcare_cloud.commands.deploy.utils import announce_deploy_start
from commcare_cloud.commands.utils import run_fab_task
from commcare_cloud.fab.deploy_diff import DeployDiff
from commcare_cloud.fab.git_repo import get_github, github_auth_provided


def deploy_commcare(environment, args, unknown_args):
    deploy_revs, diffs = get_deploy_revs_and_diffs(environment, args)

    if not confirm_deploy(environment, deploy_revs, diffs, args):
        return 1

    fab_func_args = get_deploy_commcare_fab_func_args(args)
    fab_settings = [args.fab_settings] if args.fab_settings else []
    for name, rev in deploy_revs.items():
        var = 'code_branch' if name == 'commcare' else '{}_code_branch'.format(name)
        fab_settings.append('{}={}'.format(var, rev))

    announce_deploy_start(environment, "CommCare HQ")
    return commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                   '--set', ','.join(fab_settings),
                   branch=args.branch, *unknown_args)


def confirm_deploy(environment, deploy_revs, diffs, args):
    if diffs:
        message = (
            "Whoa there bud! You're deploying non-default. "
            "\n{}\n"
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format('/n'.join(diffs))
        if not ask(message, quiet=args.quiet):
            return False

    if not _confirm_translated(environment, quiet=args.quiet):
        return False

    # do this first to get the git prompt out the way
    repo = get_github().get_repo('dimagi/formplayer') if github_auth_provided() else None

    deployed_version = _get_deployed_version(environment)
    latest_version = repo.get_commit(deploy_revs['commcare']).sha

    diff = DeployDiff(repo, deployed_version, latest_version, new_version_details=deploy_revs)
    diff.print_deployer_diff()
    return ask(
        'Are you sure you want to preindex and deploy to '
        '{env}?'.format(env=environment.name), quiet=args.quiet)


def _confirm_translated(environment, quiet=False):
    if datetime.now().isoweekday() != 3 or environment.meta_config.deploy_env != 'production':
        return True
    return ask(
        "It's the weekly Wednesday deploy, did you update the translations "
        "from transifex? Try running this handy script from the root of your "
        "commcare-hq directory:\n./scripts/update-translations.sh\n",
        quiet=quiet
    )


def _get_deployed_version(environment):
    from fabric.api import cd, sudo

    def _task():
        with cd(environment.remote_conf.code_current):
            return sudo('git rev-parse HEAD')

    host = environment.sshable_hostnames_by_group["django_manage"][0]
    environment.translate_host("django_manage")
    return run_fab_task(_task, host, 'ansible', environment.get_ansible_user_password())


def get_deploy_commcare_fab_func_args(args):
    fab_func_args = []

    if args.quiet:
        fab_func_args.append('confirm=no')
    if args.resume:
        fab_func_args.append('resume=yes')
    if args.skip_record:
        fab_func_args.append('skip_record=yes')

    if fab_func_args:
        return ':{}'.format(','.join(fab_func_args))
    else:
        return ''


def get_deploy_revs_and_diffs(environment, args):
    """Check the revisions to deploy from the arguments against the
    defaults configured for the environment and return the final
    revisions to deploy and whether they are different from the defaults.
    """
    default_branch = environment.fab_settings_config.default_branch
    branches = [
        ('commcare', 'commcare_rev', default_branch),
    ]
    for repo in environment.meta_config.git_repositories:
        branches.append((repo.name, '{}_rev'.format(repo.name), repo.version))

    diffs = []
    actuals = {}
    for repo_name, arg_name, default in branches:
        actual = getattr(args, arg_name, None)
        actuals[repo_name] = actual or default
        if actual and actual != default:
            diffs.append("'{}' repo: {} != {}".format(repo_name, default, actual))

    return actuals, diffs
