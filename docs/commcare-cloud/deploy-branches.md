# Deploying specific branches

In some cases it may be desirable to have full control over what code is deployed. This can
be accomplished by creating a `deploy_branches.yml` configuration file for you environment.
This file defined exactly which branches will get deployed.

The format of the file is as follows:

```yaml
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
```
When not specified, a submodule's trunk and name inherit from the parent.

Multiple repositories can also be specified:

```yaml
   dimagi/commcare-hq:  # this repo is required
     trunk: master
     ...

   another/repo:
     trunk: master
     ...
```

To add some safety around this file you should use the `commit-deploy-branches` script:
```bash
$ scripts/commit-deploy-branches --push
```

## Building the branch
This configuration file can be used to build a deploy branch:

```bash
$ git checkout master
$ scripts/rebuild-deploy-branch <env> --commcare-hq-root=/path/to/commcare/repo/
```

Once the branch has been built you can deploy it using the normal deploy workflow and either
specifying the branch via `--commcare-rev` or by setting `default_branch` in `<env>/fab-settings.yml`.

If you are using multiple repositories you can override the default branch for additional repositories
by passing arguments names as follows: `--{repository name}-rev`

## Conflict Resolution

First, determine where the conflict lies.
a). branch `foo` conflicts with `master`

```bash
$ git checkout -b foo origin/foo
$ git pull origin master

# try to resolve conflict

$ git push origin foo
```

b). branch `foo` conflicts with branch `bar`

You can't just merge foo into bar or vice versa, otherwise the PR
for foo will contain commits from bar.  Instead make a third,
conflict-resolution branch:

```bash
$ git checkout -b foo+bar --no-track origin/foo
$ git pull origin bar

# try to resolve conflict

$ git push origin foo+bar
```

Now add the branch `foo+bar` to `deploy_branches.yml` and move branches foo and
bar to right below it.

Later on branch B gets merged into master and removed from `deploy_branches.yml`.

Perhaps the person who removes it also notices the A+B and does the
following. Otherwise anyone who comes along and sees A+B but not both
branches can feel free to assume the following need to be done.

* Merge A+B into A. Since B is now gone, you want to merge the
 resolution into A, otherwise A will conflict with master.

* Remove A+B from `deploy_branches.yml`. It's no longer necessary since it's
 now a subset of A.

If you are unsure of how to resolve a conflict, notify the branch owner.
