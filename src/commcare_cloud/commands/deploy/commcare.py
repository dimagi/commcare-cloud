from datetime import datetime

import pytz

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_notice
from commcare_cloud.commands.deploy.sentry import update_sentry_post_deploy
from commcare_cloud.commands.deploy.utils import announce_deploy_start, announce_deploy_success
from commcare_cloud.commands.terraform.aws import get_default_username
from commcare_cloud.commands.utils import run_fab_task
from commcare_cloud.events import publish_deploy_event
from commcare_cloud.fab.deploy_diff import DeployDiff
from commcare_cloud.fab.git_repo import get_github, github_auth_provided


def deploy_commcare(environment, args, unknown_args):
    deploy_revs, diffs = get_deploy_revs_and_diffs(environment, args)

    if not confirm_deploy(environment, deploy_revs, diffs, args):
        print(color_notice("Aborted by user"))
        return 1

    fab_func_args = get_deploy_commcare_fab_func_args(args)
    fab_settings = [args.fab_settings] if args.fab_settings else []
    for name, rev in deploy_revs.items():
        var = 'code_branch' if name == 'commcare' else '{}_code_branch'.format(name)
        fab_settings.append('{}={}'.format(var, rev))

    announce_deploy_start(environment, "CommCare HQ")
    start = datetime.utcnow()
    rc = commcare_cloud(
        environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
        '--set', ','.join(fab_settings), branch=args.branch, *unknown_args
    )
    if rc != 0:
        return rc

    diff = _get_diff(environment, deploy_revs)
    if not args.skip_record:
        record_successful_deploy(environment, diff, start)

    return 0


def confirm_deploy(environment, deploy_revs, diffs, args):
    if diffs:
        message = (
            "Whoa there bud! You're deploying non-default. "
            "\n{}\n"
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format('/n'.join(diffs))
        if not ask(message, quiet=args.quiet):
            return False

    if not (
        _confirm_translated(environment, quiet=args.quiet) and
        _confirm_environment_time(environment, quiet=args.quiet)
    ):
        return False

    diff = _get_diff(environment, deploy_revs)
    diff.print_deployer_diff()
    if diff.deployed_commit_matches_latest_commit and not args.quiet:
        _print_same_code_warning(deploy_revs['commcare'])
    return ask(
        'Are you sure you want to preindex and deploy to '
        '{env}?'.format(env=environment.name), quiet=args.quiet)


DEPLOY_DIFF = None


def _get_diff(environment, deploy_revs):
    global DEPLOY_DIFF
    if DEPLOY_DIFF is not None:
        return DEPLOY_DIFF

    repo = get_github().get_repo('dimagi/commcare-hq') if github_auth_provided() else None

    deployed_version = _get_deployed_version(environment)
    latest_version = repo.get_commit(deploy_revs['commcare']).sha if repo else None

    DEPLOY_DIFF = DeployDiff(repo, deployed_version, latest_version, new_version_details=deploy_revs)
    return DEPLOY_DIFF


def _confirm_translated(environment, quiet=False):
    if datetime.now().isoweekday() != 3 or environment.meta_config.deploy_env != 'production':
        return True
    return ask(
        "It's the weekly Wednesday deploy, did you update the translations "
        "from transifex? Try running this handy script from the root of your "
        "commcare-hq directory:\n./scripts/update-translations.sh\n",
        quiet=quiet
    )


def _confirm_environment_time(environment, quiet=False):
    window = environment.fab_settings_config.acceptable_maintenance_window
    if window:
        d = datetime.now(pytz.timezone(window['timezone']))
        if window['hour_start'] <= d.hour < window['hour_end']:
            return True
    else:
        return True

    message = (
        "Whoa there bud! You're deploying '%s' outside the configured maintenance window. "
        "The current local time is %s.\n"
        "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
    ) % (environment.name, d.strftime("%-I:%M%p on %h. %d %Z"))
    return ask(message, quiet=quiet)


def _print_same_code_warning(code_branch):
    if code_branch == 'master':
        branch_specific_msg = "Perhaps you meant to merge a PR or specify a --set code_branch=<branch> ?"
    elif code_branch == 'enterprise':
        branch_specific_msg = (
            "Have you tried rebuilding the enterprise branch (in HQ directory)? "
            "./scripts/rebuildstaging --enterprise"
        )
    elif code_branch == 'autostaging':
        branch_specific_msg = (
            "Have you tried rebuilding the autostaging branch (in HQ directory)? "
            "./scripts/rebuildstaging"
        )
    else:
        branch_specific_msg = (
            "Did you specify the correct branch using --set code_branch=<branch> ?"
        )

    print(
        f"Whoa there bud! You're deploying {code_branch} which happens to be "
        f"the same code as was previously deployed to this environment.\n"
        f"{branch_specific_msg}\n"
        f"Is this intentional?"
    )


def record_successful_deploy(environment, diff, start_time):
    end_time = datetime.utcnow()

    update_sentry_post_deploy(environment, "formplayer", diff.repo, diff, start_time, end_time)
    announce_deploy_success(environment, diff.get_email_diff())
    publish_deploy_event("deploy_success", "commcare", environment)

    delta = end_time - start_time
    args = [
        '--user', get_default_username(),
        '--environment', environment.meta_config.deploy_env,
        '--url', diff.url,
        '--minutes', str(int(delta.total_seconds() // 60)),
        '--commit', diff.deploy_commit,
    ]
    commcare_cloud(environment.name, 'django-manage', 'record_deploy_success', *args)


def _get_deployed_version(environment):
    from fabric.api import cd, sudo

    def _task():
        with cd(environment.remote_conf.code_current):
            return sudo('git rev-parse HEAD')

    host = environment.sshable_hostnames_by_group["django_manage"][0]
    res = run_fab_task(_task, host, 'ansible', environment.get_ansible_user_password())
    return res[host]


def get_deploy_commcare_fab_func_args(args):
    fab_func_args = []

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
