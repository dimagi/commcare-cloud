import shlex
from datetime import datetime, timedelta

import pytz

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_error, color_notice, color_summary
from commcare_cloud.commands.ansible.run_module import (
    AnsibleContext,
    BadAnsibleResult,
    ansible_json,
    run_ansible_module,
)
from commcare_cloud.commands.ansible.ansible_playbook import run_ansible_playbook
from commcare_cloud.commands.deploy.deploy_diff import DeployDiff
from commcare_cloud.commands.deploy.sentry import update_sentry_post_deploy
from commcare_cloud.commands.deploy.utils import (
    record_deploy_start,
    announce_deploy_success,
    create_release_tag,
    within_maintenance_window,
    DeployContext,
    record_deploy_failed,
)
from commcare_cloud.events import publish_deploy_event
from commcare_cloud.const import DATE_FMT
from commcare_cloud.github import github_repo


def deploy_commcare(environment, args, unknown_args):
    deploy_revs, diffs = get_deploy_revs_and_diffs(environment, args)
    if not confirm_deploy(environment, deploy_revs, diffs, args):
        print(color_notice("Aborted by user"))
        return 1

    context = DeployContext(
        service_name="CommCare HQ",
        revision=args.commcare_rev,
        diff=_get_diff(environment, deploy_revs, args.resume),
        start_time=datetime.utcnow(),
        resume=args.resume
    )

    should_record = not (args.skip_record or args.private)
    if should_record:
        record_deploy_start(environment, context)

    ansible_args = []
    if not args.resume:
        ansible_args.extend(["-e", f"code_version={context.diff.deploy_commit}"])
    if args.private and not args.keep_days:
        args.keep_days = 1
    if args.keep_days:
        until = (datetime.utcnow() + timedelta(days=args.keep_days)).strftime(DATE_FMT)
        ansible_args.extend(["-e", f"keep_until={until}"])
    if args.private:
        if not args.limit:
            args.limit = "django_manage"
        ansible_args.append("--tags=private_release")
    else:
        if args.limit:
            exit("--limit is not allowed except with --private")
    if args.ignore_kafka_checkpoint_warning:
        ansible_args.extend(["-e", "ignore_kafka_checkpoint_warning=true"])
    if args.update_config:
        ansible_args.extend(["-e", "update_config=true"])
    ansible_args.extend(unknown_args)
    rc = run_ansible_playbook(
        'deploy_hq.yml',
        AnsibleContext(args, environment),
        quiet=True,
        skip_check=True,
        always_skip_check=True,
        respect_ansible_skip=True,
        use_factory_auth=False,
        limit=args.limit,
        unknown_args=ansible_args,
    )

    if rc != 0:
        resume_option = color_notice(f"--resume={environment.release_name}")
        print(color_error("Deploy failed."))
        print(f"Add {resume_option} to the deploy command to retry.")
        if should_record:
            record_deploy_failed(environment, context)
        return rc

    if should_record:
        record_successful_deploy(environment, context)
    if args.private:
        print(color_summary("Your private release is located here:"))
        print(color_summary(environment.remote_conf.code_source))

    return 0


def confirm_deploy(environment, deploy_revs, diffs, args):
    if args.private:
        return True

    if args.resume:
        print(f"Resuming {args.resume} release.\n")
        return _ask_to_deploy(environment.name, args.quiet)

    if diffs:
        message = (
            "Whoa there bud! You're deploying non-default. "
            "\n{}\n"
            "ARE YOU DOING SOMETHING EXCEPTIONAL THAT WARRANTS THIS?"
        ).format('/n'.join(diffs))
        if not ask(message, quiet=args.quiet):
            return False

    if not (
        _confirm_translated(environment, quiet=args.quiet)
        and _confirm_environment_time(environment, quiet=args.quiet)
    ):
        return False

    diff = _get_diff(environment, deploy_revs, args.resume)
    diff.print_deployer_diff()
    if diff.deployed_commit_matches_latest_commit and not args.quiet:
        _print_same_code_warning(deploy_revs['commcare'])
    return _ask_to_deploy(environment.name, args.quiet)


def _ask_to_deploy(env_name, quiet):
    return ask(f'Are you sure you want to deploy to {env_name}?', quiet=quiet)


DEPLOY_DIFF = None


def _get_diff(environment, deploy_revs, is_resume):
    global DEPLOY_DIFF
    if DEPLOY_DIFF is not None:
        return DEPLOY_DIFF

    tag_commits = environment.fab_settings_config.tag_deploy_commits
    repo = github_repo('dimagi/commcare-hq', require_write_permissions=tag_commits)

    deployed_version = get_deployed_version(environment)
    if is_resume:
        version_being_deployed = get_deployed_version(environment, from_source=True)
    else:
        version_being_deployed = repo.get_commit(deploy_revs['commcare']).sha if repo else None

    new_version_details = {
        'Branch deployed': ', '.join([f'{repo}: {ref}' for repo, ref in deploy_revs.items()])
    }
    if environment.fab_settings_config.custom_deploy_details:
        new_version_details.update(environment.fab_settings_config.custom_deploy_details)
    DEPLOY_DIFF = DeployDiff(
        repo, deployed_version, version_being_deployed, environment,
        new_version_details=new_version_details,
        generate_diff=environment.fab_settings_config.generate_deploy_diffs
    )
    return DEPLOY_DIFF


def _confirm_translated(environment, quiet=False):
    if datetime.now().isoweekday() != 3 or environment.meta_config.deploy_env != 'production':
        return True
    github_update_translations_pr_link = \
        "https://github.com/dimagi/commcare-hq/pulls?" \
        "q=is%3Apr+Update+Translations+author%3Aapp%2Fgithub-actions+is%3Aopen"
    return ask(
        "It's the weekly Wednesday deploy, did you update the translations "
        "from transifex?\n"
        f"Visit {github_update_translations_pr_link} "
        'and review and merge the latest automated "Update Translations" pull request.\n',
        quiet=quiet
    )


def _confirm_environment_time(environment, quiet=False):
    if within_maintenance_window(environment):
        return True
    window = environment.fab_settings_config.acceptable_maintenance_window
    d = datetime.now(pytz.timezone(window['timezone']))
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


def record_successful_deploy(environment, context):
    end_time = datetime.utcnow()

    diff = context.diff
    create_release_tag(environment, diff.repo, diff)
    update_sentry_post_deploy(environment, "commcarehq", diff.repo, diff, context.start_time, end_time)
    announce_deploy_success(environment, context)
    call_record_deploy_success(environment, context, end_time)
    publish_deploy_event("deploy_success", "commcare", environment)


def call_record_deploy_success(environment, context, end_time):
    delta = end_time - context.start_time
    args = [
        '--user', context.user,
        '--environment', environment.meta_config.deploy_env,
        '--url', context.diff.url,
        '--minutes', str(int(delta.total_seconds() // 60)),
        '--commit', context.diff.deploy_commit,
    ]
    commcare_cloud(environment.name, 'django-manage', 'record_deploy_success', *args)


def get_deployed_version(environment, from_source=False):
    if from_source:
        release = environment.remote_conf.code_source
    else:
        release = environment.remote_conf.code_current
    code_current = shlex.quote(release)
    res = run_ansible_module(
        AnsibleContext(None, environment),
        "django_manage",
        "shell",
        f"sudo -iu cchq bash -c 'git --git-dir={code_current}/.git rev-parse HEAD'",
        become=False,
        run_command=ansible_json,
    )
    result = next(iter(res.values()), {"stderr": "no result for host"})
    if "stdout" in result:
        return result["stdout"]
    error = result["stderr"] if "stderr" in result else repr(result)
    if "rc" in result:
        error += f"\n\nreturn code: {result['rc']}"
    raise BadAnsibleResult(error)


def get_deploy_revs_and_diffs(environment, args):
    """Check the revisions to deploy from the arguments against the
    defaults configured for the environment and return the final
    revisions to deploy and whether they are different from the defaults.
    """
    default_branch = environment.fab_settings_config.default_branch
    branches = [('commcare', 'commcare_rev', default_branch)]

    diffs = []
    actuals = {}
    for repo_name, arg_name, default in branches:
        actual = getattr(args, arg_name, None)
        actuals[repo_name] = actual or default
        if actual and actual != default:
            diffs.append("'{}' repo: {} != {}".format(repo_name, default, actual))

    return actuals, diffs
