Deploying from the private code repo
====================================

``--private-repo`` deploys the commcare component from the repo named by
an environment's ``private_code_repo`` setting instead of ``code_repo``.

.. code-block:: bash

    commcare-cloud <env> deploy commcare --private-repo --commcare-rev=<rev>
    commcare-cloud <env> deploy-diff commcare --private-repo --commcare-rev=<rev>

``--commcare-rev`` is required with ``--private-repo`` (except when
resuming). The option only applies to the commcare component; it is
rejected for formplayer-only deploys. It is independent of ``--private``, which
selects a private release.

Requirements
------------

- ``private_code_repo`` is set in the environment's ``fab-settings.yml``
  to the repo's SSH GitHub URL.
- The environment secret ``private_code_repo_deploy_key`` holds the private key
  of a read-only GitHub deploy key for that repo. The key is multi-line, so set
  it with ``commcare-cloud <env> secrets edit private_code_repo_deploy_key --from-stdin``.
- The deployer's GitHub SSH key (from the SSH agent, which is forwarded to the
  control machine) can read the repo. ``--commcare-rev`` must be a branch, tag,
  or full commit SHA.
- If ``tag_deploy_commits`` is enabled, the release tag is pushed to the
  private repo using the deployer's own SSH key, which needs write access to
  it. Otherwise tagging fails with an error message, but the deploy continues.

On the servers, the key is written to ``~cchq/.ssh/private_code_repo_deploy_key``
and is used only for cloning that repo (not its submodules). GitHub's host key
is checked against the copy bundled with commcare-cloud.

Notes
-----

- Pass ``--private-repo`` again when using ``--resume`` on a release that
  was started with it.
- The deploy diff lists the public pull requests included in the deploy, by
  comparing the public commits it is based on. Its link is labeled as public
  changes only, with the number of commits that are only in the private repo
  and the commit that was actually deployed. Private-only commits are not
  listed, and are not sent to Sentry.
- Finding those public commits uses a commit-only git cache of commcare-hq
  history at ``~/.cache/commcare-cloud/commcare-hq-commits.git`` (about 55 MB).
  It is created on first use, which takes a minute or less.
