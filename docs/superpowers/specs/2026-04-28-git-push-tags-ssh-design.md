# Push deploy tags via SSH instead of GitHub API

## Context

When `cchq <env> --control deploy` runs, the deploy script tags the deployed commit by calling the GitHub REST API (`repo.create_git_ref`). This requires a Personal Access Token with write permissions, which is prompted for interactively (`getpass`) if not present in the environment or config. The prompt slows down the deploy and adds friction.

The deploy is invoked with `--control`, which re-runs the `cchq` command on the control machine via SSH. Agent forwarding (`-A`) is automatically enabled when sshing to the control host (`src/commcare_cloud/commands/inventory_lookup/inventory_lookup.py:132`), so the user's SSH agent is reachable from control. We can use that to do a native `git push` instead of an API call, removing the PAT requirement for tag creation.

## Goal

Replace the GitHub-API-based tag creation with a native `git push` over SSH that authenticates via the forwarded SSH agent. Drop the now-unneeded write-scope PAT prompt.

## Non-goals

- Changing the tag name format.
- Changing when tags are created (still gated on `fab_settings_config.tag_deploy_commits`).
- Changing the contract on failure (tagging is best-effort; deploy is still recorded as successful if tagging fails).
- Removing the optional read-only `GITHUB_TOKEN` for higher rate limits on diff/compare API calls.

## Design

### Tag push mechanism: ephemeral bare clone

`create_release_tag` in `src/commcare_cloud/commands/deploy/utils.py` is rewritten to push the tag via git instead of the GitHub API. The push runs on the control machine (where deploy already runs), using a temp bare repo created and discarded per call:

```
tmp = mkdtemp()
git -C tmp init --bare
git -C tmp fetch --depth=1 <ssh-url> <deploy_commit>
git -C tmp push <ssh-url> <deploy_commit>:refs/tags/<tag-name>
shutil.rmtree(tmp)
```

The fetch-by-SHA relies on GitHub's default `uploadpack.allowReachableSHA1InWant=true`. The fetch transfers one commit + its tree (small); the push only updates a ref, no objects sent.

A persistent clone on the control machine was considered and rejected: a one-time `git clone` of `commcare-hq` is several hundred MB, and the upkeep (pruning, recovery from corruption) is more lifetime liability than is justified for one tag per deploy.

### Tag name and SSH URL

- **Tag name**: unchanged. `f"{environment.release_name}-{environment.name}-deploy"`.
- **SSH URL**: derived from the PyGithub `repo` object passed to `create_release_tag`, formatted as `f"git@github.com:{repo.full_name}.git"`. Reuses the repo identity already established by the caller; no new config knob, no second hardcoded list of `dimagi/commcare-hq` and `dimagi/formplayer`.

### Function shape

`create_release_tag(environment, repo, diff)` keeps its current signature and call sites (`commcare.py:214`, `formplayer.py:110`). The body becomes a small driver that builds the SSH URL and tag name, then delegates to a private helper:

```python
def _push_release_tag(remote_url, sha, tag_name):
    # init bare, fetch, push, cleanup; raises on subprocess failure
```

Splitting the helper out keeps the URL/tag-name construction in `create_release_tag` (close to the `environment`/`repo` context) while letting tests drive `_push_release_tag` directly with a `file://` URL.

### Failure handling

`create_release_tag` wraps the call in `try/except subprocess.CalledProcessError` (and `OSError` for git-not-installed cases). On failure it prints a warning via `color_error` and returns. The deploy still records as successful — same contract as today's `except GithubException`.

No preflight check on `SSH_AUTH_SOCK` or `ssh-add -L` — corner case the warning text already covers.

### `github.py` simplification

With the PAT-write requirement gone, `src/commcare_cloud/github.py` shrinks:

1. Drop `require_write_permissions` and `repo_is_private` parameters from `github_repo()`. Drop the post-construction `repo.permissions.push` check.
2. Delete `get_github_credentials()` (the prompting variant). Only `get_github_credentials_no_prompt()` remains; `GITHUB_TOKEN` env or `config.py` still works for higher rate limits.
3. Update callers in `commcare.py:144-145` and `formplayer.py:56-57`: stop computing `tag_commits` for the `github_repo()` call, drop the `require_write_permissions=...` argument.

Verified the deploy path is the only consumer of these surfaces — `get_github_credentials` has no external callers, and `github_repo()` is only imported in `commcare.py:26` and `formplayer.py:27`.

The legacy-config deprecation warning (printed for years from `get_github_credentials`) is collateral damage. The change is operator-invisible during normal deploys (no prompt anymore), so we are not adding a dedicated changelog entry.

## Testing

A new `tests/test_deploy/test_create_release_tag.py` follows the `test_git_setup_release.py` pattern: real git subprocesses against an on-disk bare repo via `file://` URL, no mocks of `subprocess`/`git`.

Test cases:

1. **Happy path** — `_push_release_tag(file_url, sha, tag_name)` against a bare repo containing the SHA; assert `refs/tags/<tag_name>` in the bare repo points at the expected SHA.
2. **Push failure** — point at a non-existent URL; assert `create_release_tag` returns without raising and prints a warning. Drives the public function so the `try/except` is exercised.
3. **`tag_deploy_commits=False`** — assert the early-return guard is preserved (no git commands run).

The test fixture creates a small bare repo with one commit; no need to bundle a tarball like `mock-hq.git.tbz` for this scope.

## Out-of-scope follow-ups

- Replacing the read-only diff API (`repo.compare`, `repo.get_commit`) with anything else. Keeps PyGithub on the read path.
- Generalizing `create_release_tag` to non-GitHub remotes. The hardcoded `git@github.com:` URL is fine until proven otherwise.
