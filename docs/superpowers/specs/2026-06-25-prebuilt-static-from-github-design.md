# Pull prebuilt static files from GitHub during deploy

## Status

Phase 1 design — Dimagi internal deploys only (proof of mechanism).

## Problem

Today, every CommCare HQ deploy builds static files **on the hosts** via the
`deploy_hq` ansible role: `staticfiles_collect` (on webworkers + proxy) runs
`resource_static`, `collectstatic`, `fix_less_imports_collectstatic`,
`generate_webpack_settings`, and `yarn build`; `staticfiles_compress` (on
`proxy[0]`) runs `compress --force` and distributes `staticfiles/CACHE` to the
other hosts (via `shared_dir_for_staticfiles` or by pushing the manifest to
redis).

This build is slow, requires Node/yarn/SASS build toolchains on production
hosts, and repeats work that the `Build Static Files` GitHub Actions workflow
(`.github/workflows/build-static.yml` in commcare-hq) already performs on every
push to `autostaging`. That workflow produces `REQUIRED_STATIC_FILES.zip`, but
the artifact currently requires an interactive GitHub login to download, so
commcare-cloud cannot consume it.

**Goal:** have commcare-cloud download the prebuilt artifact for the deployed
commit and distribute it to the hosts, eliminating the on-host build — proven
first on Dimagi internal (staging) deploys.

## Scope

### In scope (Phase 1)

- Dimagi **internal** deploys only (autostaging / staging).
- Fetch the GitHub Actions artifact for the deploy's SHA via the **REST API**
  (no `gh` CLI — raw `curl`).
- Authenticate with the **same GitHub token the user already supplies for the
  deploy summary/diff** (resolved by
  `commcare_cloud.github.get_github_credentials_no_prompt()`: the
  `GITHUB_TOKEN` env var or `config.py`'s `GITHUB_APIKEY`). The token must have
  `Actions: Read` on `dimagi/commcare-hq`.
- Download on the **control machine**, unwrap GitHub's outer zip, then push the
  inner `REQUIRED_STATIC_FILES.zip` to the hosts and unzip it there. The token
  never lands on a host.
- **Fall back** to the existing on-host build when the artifact is unavailable.

### Explicitly out of scope (future phases)

- Third-party hosters consuming the artifact. They continue to build on-host
  exactly as today (no behavior change, no Dimagi credential required).
- Permanence beyond the 90-day artifact retention (e.g. release assets in a
  dedicated side repo).
- Production deploys.
- A dedicated artifact credential (e.g. an org-owned GitHub App or a separate
  fine-grained PAT in commcare-cloud secrets). Reusing the deploy-summary token
  is the fastest internal test; revisit once the mechanism is proven.

## Key facts established during design

- **The artifact matches the deploy commit exactly.** The workflow
  (`.github/workflows/build-static.yml` in commcare-hq) names the artifact
  `staticfiles-${{ github.sha }}` — the full 40-char commit SHA of the
  autostaging push. The deploy fetches `staticfiles-<code_version>` where
  `code_version` is the resolved deploy commit, so the fetched static files
  can never belong to a different commit than the one being deployed.
- **Inner zip layout (verified in commcare-hq).**
  `copy_required_static_files` zips the `REQUIRED_STATIC_FILES/` directory
  with `arcname` relative to that directory, so the zip's entries are bare
  top-level dirs (`hqwebapp/`, `CACHE/`, `jsi18n/`, `webpack/`, ...) with no
  wrapper directory. On the hosts it unzips directly into
  `{{ code_source }}/staticfiles/` (host `STATIC_ROOT`).
- **The artifact is sufficient.** `REQUIRED_STATIC_FILES.zip` already contains
  the fully built `staticfiles/` subset — app static dirs, `jsi18n`, `webpack`,
  `webpack_b3`, and `CACHE/` including the compressed assets and
  `manifest.json`. When the artifact is used, the entire on-host build chain is
  skipped.
- **Artifact download requires a bearer token**, even for a public repo, and
  even though commcare-hq is public. SSH-agent forwarding (which carries SSH
  keys for git, not an HTTPS token) cannot authenticate this REST call — hence
  the PAT is required, not optional, in the absence of `gh`.
- **GitHub wraps the artifact in a zip-of-zip.** The artifact-download endpoint
  returns an outer zip containing our `REQUIRED_STATIC_FILES.zip`. The control
  machine unzips **once** (removing GitHub's wrapper) and ships the inner zip
  to the hosts; the second unzip happens on each host. If a download is ever
  not double-wrapped, the control machine skips the unwrap and pushes the zip
  as-is.
- **Why not private S3:** a private bucket would exclude third-party hosters
  (future goal), and a public bucket would expose Dimagi to anonymous
  download/bill-inflation. GitHub hosting puts bandwidth cost on GitHub and
  per-token rate limits on the caller.

## Design

### Transport & auth

- **Reuse the deploy-summary token.** The deploy command already resolves a
  GitHub token via `commcare_cloud.github.get_github_credentials()`
  (`GITHUB_TOKEN` env var, `config.py` `GITHUB_APIKEY`, or the memoized
  interactive `getpass` prompt) to compile the deploy summary/diff. The
  artifact fetch uses the same token — no new secret, no changes to
  `secrets_schema.py`/`secrets.yml`. The deploy command exports the token as
  `GITHUB_TOKEN` in the `ansible-playbook` subprocess environment
  (`build_env()` copies `os.environ`); it never appears in `-e` args, any
  command line, or output. Users must ensure their token has `Actions: Read`
  on `dimagi/commcare-hq` (classic tokens with `public_repo` already do).
- **Fetch timing: at the static files step, not at deploy start.** The deploy
  command downloads nothing; it only passes a non-secret
  `-e prebuilt_static=true`. The playbook fetches the artifact when it
  reaches the static files step. By then the release-setup plays (checkout,
  yarn install, ...) have given the GitHub Actions build 10–15 minutes to
  finish, so waiting on a still-running build is rare, and any poll happens
  exactly where the time is needed instead of blocking the whole deploy
  upfront.
- GitHub REST calls:
  1. `GET /repos/dimagi/commcare-hq/actions/artifacts?name=staticfiles-<sha>`
     → resolve the artifact id (the `name` query filter avoids pagination).
  2. `GET /repos/dimagi/commcare-hq/actions/workflows/build-static.yml/runs?head_sha=<sha>`
     → only when (1) finds nothing: check whether the build for this exact
     commit is queued/in progress. If it is, **wait and poll** until it
     completes and the artifact appears; if no run exists or the run
     concluded without success, fail fast to the on-host fallback instead
     of polling pointlessly.
  3. `GET /repos/dimagi/commcare-hq/actions/artifacts/<id>/zip` → 302 redirect
     to a short-lived blob URL; the byte transfer is **not** counted against
     the API rate limit.
  Waiting on a running build adds a pair of type-(1)/(2) calls per poll
  interval. Authenticated limit is 5,000/hr — negligible.

### Opt-in configuration

The prebuilt-static path is **opt-in per deploy** via a new CLI flag on the
deploy command: `cchq <env> deploy commcare --prebuilt-static`. No environment
config or schema change — deploys that omit the flag (all third parties, and
any Dimagi deploy not opting in) keep the existing on-host build untouched. A
GitHub token (see Transport & auth) must also be present for the path to
activate; without one, deploys fall back to the on-host build.

### New ansible tasks: `staticfiles_fetch`

A new `deploy_hq` task file `staticfiles_fetch.yml`, run on the **control
machine** (`delegate_to: localhost`, `run_once: true`) immediately before the
static files plays, gated on `prebuilt_static`. It invokes the Python helper
as a CLI — `python -m commcare_cloud.commands.deploy.static_artifact
<code_version> <temp dir>` — which reads `GITHUB_TOKEN` from the inherited
environment (never argv), prints the fetched zip path on success, and exits
nonzero when the artifact is unavailable so the play can fall back. The
helper:

1. **Resolve + wait on running build.** Call REST endpoint (1) for
   `staticfiles-<code_version>`. If the artifact isn't there yet, check the
   build-static workflow run for that SHA (endpoint (2)): while it is
   queued/in progress, poll up to a bounded timeout; if there is no run or
   it finished unsuccessfully, give up immediately. On success capture the
   artifact id.
2. **Download + unwrap once.** Call endpoint (3) with the token, follow the
   redirect, and download into a control-machine temp dir. If the download is
   double-zipped (GitHub's wrapper around `REQUIRED_STATIC_FILES.zip`), unzip
   **once** to extract the inner zip; otherwise use the download as-is. The
   inner zip is what gets pushed to hosts — the control machine never expands
   the full `staticfiles/` tree. Verify (e.g. `unzip -l`) that the zip's
   internal root maps onto host `STATIC_ROOT`
   (`{{ code_source }}/staticfiles/`); note the management command
   `copy_required_static_files` writes into a `REQUIRED_STATIC_FILES/`
   directory, so the internal root must be checked during implementation.
3. **Set fact** `static_artifact_available: true|false` for the whole play.

### Distribution

When `static_artifact_available`:

- **Push the zip, unzip on the hosts.** Copy the single
  `REQUIRED_STATIC_FILES.zip` from the control machine to a temp path on each
  webworker/proxy (ansible `copy` or `synchronize` push), then `unarchive` it
  on each host into `{{ code_source }}/staticfiles/`, and remove the temp zip.
  Shipping one compressed file is faster and cheaper than rsyncing the
  expanded tree of many small files.
- Reuse the existing CACHE/manifest distribution: push the manifest to redis
  (`update_manifest save`) or to `shared_dir_for_staticfiles`, matching the
  current `staticfiles_compress` behavior.

### Gating / fallback

- The fetch task runs immediately before the static files plays (only when
  `--prebuilt-static` was passed and a token was present, i.e.
  `prebuilt_static=true` reached the play).
- The existing `staticfiles_collect` and `staticfiles_compress` plays in
  `deploy_hq.yml` gain `when: not static_artifact_available`, becoming the
  universal default and the fallback. Any failure in `staticfiles_fetch`
  (missing artifact, download error, layout mismatch) sets
  `static_artifact_available: false` and the on-host build runs.

## Build approach: vertical slices

Implement the feature as thin end-to-end slices, each independently
deployable/testable against staging, rather than layer-by-layer:

1. **Slice 1 — fetch machinery + flag.** The Python helper (artifact lookup +
   wait-on-running-build + download + single unwrap + progress output) with
   its CLI entry point, the `--prebuilt-static` flag, and the token/env
   plumbing (`-e prebuilt_static=true`, `GITHUB_TOKEN` exported to the
   playbook subprocess). No playbook changes; on-host build still runs
   unconditionally. Verifiable by unit tests plus running the CLI helper
   against a real autostaging SHA on the control machine.
2. **Slice 2 — playbook fetch + distribute + gate.** The `staticfiles_fetch`
   localhost task (invoking the CLI at the static files step, setting
   `static_artifact_available`), push the zip to hosts, unzip into
   `STATIC_ROOT`, manifest/CACHE distribution, and
   `when: not static_artifact_available` gating on `staticfiles_collect` /
   `staticfiles_compress`. This is the first slice that changes deploy
   behavior; verified by a staging deploy serving prebuilt static.
3. **Slice 3 — hardening.** Fallback paths (missing artifact, token without
   `Actions: Read`, layout mismatch, poll timeout), `no_log` review, and
   operator-facing messaging.

Each slice lands as its own PR with its own tests.

## Testing

- **Unit tests (Python, commcare-cloud):** artifact lookup/poll logic against
  mocked GitHub API responses — found immediately, not-yet-then-found
  (polling), and never-found (timeout → fallback). Keep the HTTP/lookup logic in
  a small testable helper rather than inline ansible.
- **Staging dry-run deploys:**
  - Artifact present → build steps skipped; app serves correctly versioned
    static (manifest resolves, webpack bundles load).
  - Artifact absent / token missing / opt-in off → on-host build runs unchanged.

## Open items for the implementation plan

- Behavior when the user's token lacks `Actions: Read` (fall back with a
  clear message).
- Whether host-side `unarchive` needs `unzip` installed on webworkers/proxies.

Resolved during planning: opt-in is the `--prebuilt-static` CLI flag; the
zip's internal root is bare top-level static dirs (see Key facts); polling
waits only while the build-static workflow run for the SHA is queued or in
progress (30s interval, 1800s ceiling), failing fast otherwise; the fetch
happens at the static files step (localhost task invoking the helper CLI),
with the token reaching it only via the playbook subprocess environment —
never `-e` args, argv, or remote hosts.
