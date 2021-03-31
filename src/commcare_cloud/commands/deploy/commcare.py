from clint.textui import indent

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_summary


def deploy_commcare(environment, args, unknown_args):
    deploy_revs, diffs = get_deploy_revs_and_diffs(environment, args)

    if not confirm_deploy(deploy_revs, diffs, args):
        return 1

    fab_func_args = get_deploy_commcare_fab_func_args(args)
    fab_settings = [args.fab_settings] if args.fab_settings else []
    for name, rev in deploy_revs:
        var = 'code_branch' if name == 'commcare' else '{}_code_branch'.format(name)
        fab_settings.append('{}={}'.format(var, rev))

    return commcare_cloud(environment.name, 'fab', 'deploy_commcare{}'.format(fab_func_args),
                   '--set', ','.join(fab_settings),
                   branch=args.branch, *unknown_args)


def confirm_deploy(deploy_revs, diffs, args):
    if diffs:
        message = (
            "Whoa there bud! You're deploying non-default. "
            "\n{}\n"
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format('/n'.join(diffs))
        if not ask(message, quiet=args.quiet):
            return False

    print(color_summary("You are about to deploy the following code:"))
    with indent():
        for name, rev in deploy_revs:
            print(color_summary("{}: {}".format(name, rev)))

    return ask('Continue with deploy?', quiet=args.quiet)


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
    default_branch = environment.fab_settings_config.default_branch
    branches = [
        ('commcare', 'commcare_rev', default_branch),
    ]
    for repo in environment.meta_config.git_repositories:
        branches.append((repo.name, '{}_rev'.format(repo.name), repo.version))

    diffs = []
    actuals = []
    for repo_name, arg_name, default in branches:
        actual = getattr(args, arg_name, None)
        actuals.append((repo_name, actual or default))
        if actual and actual != default:
            diffs.append("'{}' repo: {} != {}".format(repo_name, default, actual))

    return actuals, diffs
