# Ansible Upgrade + Test Coverage — Jira Backlog

## Context

commcare-cloud is pinned to **Ansible 4.10 (core 2.11)** on **controller Python
3.10** — years past EOL, blocking security fixes and modern syntax. Goal: reach
**Ansible 14 (core 2.21)** on **Python 3.14**.

Scale: 53 roles, 63 playbooks, ~307 YAML files, plus custom modules/plugins,
with thin automated coverage today. CI (`.tests/tests.sh`) `--syntax-check`s
`deploy_stack.yml` (the ~18 playbooks it imports) and *executes* only the
`py3,commcarehq`-tagged subset of it against a `localhost`/`local`-connection
test env, then byte-compiles the rendered `localsettings.py`. So most roles are
parse-checked but never run, and standalone playbooks outside `deploy_stack.yml`
(`deploy_hq.yml`, `deploy_prometheus.yml`, `deploy_postgres.yml`, the
`restart_*`/`deploy_citusdb`/`deploy_proxy` set, etc.) get neither. That
coverage gap is the upgrade's biggest risk, so the test tickets come first.

Sequence: clean up deprecations and build a test safety net first, then step
through versions. The interpreter may move in two hops: **3.10 → 3.12** (spans
Ansible 10–12), then **3.12 → 3.14** at the 12 → 14 jump (or one hop if 3.14
tests pass early — #32 optional).

### Highest-risk changes (v5–v14)

1. **Templating/conditional strictness**, peaking at core 2.19: string-boolean
   conditionals (v5), arithmetic outside `{{ }}` (v6), embedded-template
   conditionals (v8/CVE-2023-5764), and non-boolean `when:` as an error + native
   Jinja + inverted trust model (v12). → tickets 21–23.
2. **Collection removals** in every major — in-use ones must be pinned and
   installed explicitly. → #7–10.
3. **Collection upgrades/replacements** — see Appendix B. All four archived
   cloudalchemy roles are removed **on 4.10, ahead of the Ansible-10 bump**, so
   that bump (#28) stays a pure pin change: #12–13 self-contain the dimagi
   collection (prometheus, then alertmanager), #14 cuts the release and adopts it
   on 4.10, #15–16 vendor the two direct refs (grafana, then node_exporter) as
   repo-local roles. #31 is then an *optional* post-Ansible-10 swap of those
   vendored roles to upstream collections.
4. **Python floor jumps** (3.10 @ v9, 3.12 @ v13) and **UTF-8 locale enforced at
   startup** (v7).

---

## Backlog

"Depends" = ticket numbers. 1–2 are housekeeping; 3–6 build the test safety net;
7–27 are version-agnostic cleanup (7–18 dependency work; 19–27 deprecation
edits) and parallelize within their bands; 28–37 are mostly sequential version
bumps + rollout (31 is optional — see there). Every cleanup ticket (7–27) must
leave the tree green on 4.10 on its own, so that each bump (28/33/34) is a pin
change with nothing left to fix.

### Housekeeping — independent, do first

#### 1. Drop `gitpython`
Used once in `ops_tool.py` (`git.Repo(search_parent_directories=True)`); replace
with a `subprocess` git call and remove from `pyproject.toml`/`uv.lock`.
Acceptance: repo root still resolves; dep gone; tests green.

#### 2. Remove stale Ubuntu 18.04 references
18.04 is unsupported. Search `18.04|bionic`.
Delete `ansible_distribution_version == '18.04'` branches.
Acceptance: none remain; 22.04 path unaffected.

### Safety net — build verification before touching versions

#### 3. CI lint + syntax for all playbooks
Add `ansible-lint` (dev dep) and extend `--syntax-check` to cover the
top-level playbooks *not* reached by the existing `deploy_stack.yml` check —
`deploy_hq.yml`, `deploy_prometheus.yml`, `deploy_postgres.yml`, the
`restart_*`/`deploy_citusdb`/`deploy_proxy` set, etc. (`deploy_stack.yml` and
its ~18 imports are already syntax-checked by `.tests/tests.sh`); capture
existing violations as a baseline. Full FQCN module normalization is
low-priority baseline debt (short names resolve fine; collection moves are
handled by #7–8).
Acceptance: new non-blocking `lint.yml` fails on new violations; green on day one.

#### 4. Refresh Vagrant harness to 22.04
`Vagrantfile` is `ubuntu/bionic64` (18.04); upgrade it, verify provisioning,
document the local full-stack flow.
Acceptance: `vagrant up` + `deploy-stack` completes on 22.04 on current Ansible.

#### 5. Molecule scaffolding + one reference role
Add Molecule (docker driver) with a shared base config and a worked example for
one simple role (e.g. `swap` or `logrotate`, which already has a `tests/` stub).
Wire a Molecule job into CI. Document "how to add a Molecule scenario." Keep
test code separate from production code.
Acceptance: `molecule test` converge + idempotence green locally and in CI on 22.04.

#### 6. Molecule coverage for critical roles
Add Molecule converge/idempotence scenarios for the operationally critical,
untested roles: postgresql(_base), pgbouncer, couchdb2, kafka, redis, rabbitmq,
elasticsearch, nginx, proxy/haproxy. Likely one Jira ticket per role/group.
Acceptance: each converges twice with no changes; basic service-up asserts.
Depends: 5.

### Dependency work — collections + roles, version-agnostic, run on 4.10

#### 7. Adopt `community.postgresql` (declare + migrate `postgresql_*`)
Add `community.postgresql` to `requirements.yml`, then FQCN-ify
`postgresql_user/db/privs/set/query` and drop `encrypted:` (removed in core 2.15).
Files:
- `roles/postgresql_base/tasks/set_up_dbs.yml`
- `roles/postgresql_base/tasks/main.yml`
- any playbook needing a `collections:` entry.
Acceptance: `ansible-galaxy install -r` resolves the collection; Molecule
postgres (#6) + syntax clean.
Depends: ideally 6.

#### 8. Adopt `ansible.posix` (declare + migrate `synchronize`/`authorized_key`)
Add `ansible.posix` to `requirements.yml`, then FQCN-ify `synchronize` /
`authorized_key` in `roles/deploy_hq/tasks/staticfiles_*` and
`roles/setup_auth_keys.yml`.
Acceptance: collection installs; refs resolve to `ansible.posix.*`; lint clean.

#### 9. Audit `community.general` + the Dimagi collections
Decide whether `community.general 7.4.0` is still required and at what version,
and confirm `dimagi.commcare_prometheus` / `dimagi.commcare_logstash` load on
the target cores. Record each collection's `requires_ansible` and confirm it
admits core 2.21 (v14 excludes incompatible collections by default).
Acceptance: necessity decision recorded; a compat-matrix entry per collection.

#### 10. Removed-collection audit (collections dropped v5–v14)
The repo uses short module names (FQCN is ~6 tasks total), so grep the *short
module names* of every collection removed from the `ansible` package across
v5–v14 (per each version's changelog). Pin and explicitly install any still in
use.
Acceptance: nothing in-use silently disappears at any version step; pins added.

#### 11. Standalone-role maintenance audit; drop orphaned roles
Use the Appendix B matrix as the baseline: for each *role* in `requirements.yml`
record archived flag, last activity, target-core compatibility.
`bdellegrazie.postgres_exporter` and `gantsign.golang` appear only in
`requirements.yml` *directly*, but both are **transitive deps** of
`dimagi.commcare_prometheus` role metas (its `postgres_exporter` →
`bdellegrazie.postgres_exporter`; `agg_pushgateway_exporter` /
`airflow_exporter` → `gantsign.golang`) — not orphaned. Record the consumer;
neither is droppable as-is. (`gantsign.golang`'s version bump is #30; the four
`cloudalchemy.*` roles are handled across #12–16, with #31 the optional
post-Ansible-10 upstream swap; the dead trivial roles are #17–18.)
Acceptance: role compat matrix complete; orphaned pins removed or justified.

#### 12. Vendor the `prometheus` install into `dimagi.commcare_prometheus`
`cloudalchemy.prometheus` is archived and uses bare `include:` (removed in
Ansible 9 / core 2.16), so it must go before the Ansible-10 bump (#28). The dimagi collection's
`prometheus` role pulls it via a `meta` dependency; make that role carry its own
install instead. The collection already ships ~16 self-contained roles, so this
fits its design; **do not** re-base on `prometheus.prometheus` — its
`requires_ansible >=2.14` floor would break the collection on core 2.11.
This is a change in the **separate `dimagi/commcare-prometheus` repo** (last
released 2020-10): replace the `cloudalchemy.prometheus` `meta` dep with vendored
install tasks, written cross-version-safe (the #19–23 discipline) to run on
**core 2.11 → 2.21**; set a permissive `requires_ansible` (≥2.11). **No release
yet** — #14 cuts one release once alertmanager (#13) is also done.
Prior art: [#6520](https://github.com/dimagi/commcare-cloud/pull/6520)
(the in-place `cloudalchemy.prometheus` bump attempt) — **close here**,
superseded by vendoring the install.
Acceptance: the collection's `prometheus` role `meta` no longer lists
`cloudalchemy.prometheus`; the vendored install is cross-version-safe (proven at
#14's release/adopt).
Depends: ideally 6.
Open question on how to proceed with this upgrade:
https://dimagi.slack.com/archives/CNQ636095/p1781277055592099?thread_ts=1781210489.586889&cid=CNQ636095

#### 13. Vendor the `alertmanager` install into `dimagi.commcare_prometheus`
Same pattern as #12 for the collection's `alertmanager` role (archived
`cloudalchemy.alertmanager`, also bare-`include:`-based). Edit
`dimagi/commcare-prometheus` only; again **no release here** — #14 cuts a single
release covering both vendorings.
Acceptance: the collection's `alertmanager` role `meta` no longer lists
`cloudalchemy.alertmanager`; the vendored install is cross-version-safe.
Depends: 12 (same collection/repo, sequential).

#### 14. Release `dimagi.commcare_prometheus` + adopt it on 4.10
Cut **one** new release of `dimagi/commcare-prometheus` carrying the #12 + #13
vendoring (one release for both, not one per role — that keeps the upstream
edits as their own steps and the release/adopt as a single logical step here).
In commcare-cloud: bump the `dimagi.commcare_prometheus` pin to that release and
**drop the `cloudalchemy.prometheus` + `cloudalchemy.alertmanager` pins** from
`requirements.yml` (only the dimagi collection needed them).
`deploy_prometheus.yml`'s `dimagi.commcare_prometheus.prometheus` / `.alertmanager`
refs are unchanged — now backed by the vendored install.
After this, the collection no longer pulls any cloudalchemy role; it still pulls
`bdellegrazie.postgres_exporter` and `gantsign.golang` transitively (via its
`postgres_exporter` and Go-exporter roles) — addressed in #11/#30, not here.
Acceptance: new collection release with no `cloudalchemy.*` in any role's `meta`;
pin bumped and both pins gone; monitoring still converges on 4.10; the vendored
install runs clean through core 2.21 (re-verified at #28/#33/#34).
Depends: 12, 13.

#### 15. Vendor `cloudalchemy.grafana` as a repo-local role (on 4.10)
`cloudalchemy.grafana` is archived and referenced **directly** in
`deploy_prometheus.yml`. Its maintained upstream successor `grafana.grafana`
floors at core 2.12, so it *cannot* be adopted on 4.10 — instead fork it into a
repo-local role under `roles/` (the #17/#18 pattern — a copy we can fix forward)
and fix its removed syntax cross-version-safe (core 2.11 → 2.21, the #19–23
discipline):
- 8× bare `include:` → `include_tasks:` (`tasks/main.yml`) — `include:` removed
  in core 2.16.
- 1× `warn: false` (`tasks/dashboards.yml`) — removed in core 2.14.
- The `with_*` loops are deprecated-not-removed — fold into #20's mechanical
  pass, not required to survive the Ansible-10 bump.
Re-point `deploy_prometheus.yml` to the repo-local role and **drop the
`cloudalchemy.grafana` pin**. Without this, the Ansible-10 bump (#28) could not be
green and merged on its own (its `deploy_prometheus.yml` grafana path would be
dead), which is why the upstream swap (#31) is deferred and optional.
Acceptance: resolves to a repo-local role; no `cloudalchemy.grafana` pin/ref
remains; monitoring converges on 4.10; role syntax-checks clean (re-verified on
the new core at #28).
Depends: ideally 6.

#### 16. Vendor `cloudalchemy.node_exporter` as a repo-local role (on 4.10)
Same approach as #15 for `cloudalchemy.node-exporter` (note the legacy hyphen),
the other direct ref in `deploy_prometheus.yml`. Its successor
`prometheus.prometheus.node_exporter` floors at core 2.14. The removed-syntax
surface is smaller:
- 1× `warn: false` (`tasks/preflight.yml`) — removed in core 2.14; `main.yml`
  already uses `import_tasks`, so this subfile is the only hard break.
- The `with_*` loops fold into #20, not required to survive the Ansible-10 bump.
Re-point the ref and **drop the `cloudalchemy.node_exporter` pin**. With #14 + #15,
this removes the **last** cloudalchemy pin — zero `cloudalchemy.*` remains
anywhere, all on 4.10, before the Ansible-10 bump (#28).
Acceptance: resolves to a repo-local role; no `cloudalchemy.node_exporter`
pin/ref remains; monitoring converges on 4.10; role syntax-checks clean
(re-verified at #28).
Depends: ideally 6 (independent of #15).

#### 17. Vendor or replace `tmpreaper` (`ANXS/tmpreaper`, dead since 2017)
Abandoned but trivial; used in several playbooks. Risk is removed syntax
(`with_items`, bare `warn:`, string-bool `when:`) failing on the target core.
Fork into the repo as a local role under `roles/` (preferred — a maintainable
copy we can fix forward) or replace with a few inline tasks; re-point
`requirements.yml` / refs.
Acceptance: resolves to a repo-local role (or inline tasks); no abandoned pin
remains; touched-role Molecule green on the target core.

#### 18. Vendor or replace `ansible-logrotate` (`nickhammond`, dead since 2018)
Same approach as #17. Heavily used — it's a `meta` dependency of `common`, so
nearly every host pulls it; test broadly.
Acceptance: resolves to a repo-local role (or inline tasks); no abandoned pin
remains; `common`-dependent role Molecules green on the target core.

### Deprecation cleanup — version-agnostic, run on 4.10

#### 19. Remove `warn:` on command/shell
~15, mostly `ping.yml`; removed in core 2.14.
Acceptance: none remain; lint clean.

#### 20. Convert `with_*` to `loop:` — largest change (~125 across ~21 files)
Add appropriate filters/`lookup`. Mechanical; split on playbook and role.
Prior art: [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
[#6235](https://github.com/dimagi/commcare-cloud/pull/6235) carry the same kind
of mechanical loop/`include_tasks` rewrite, but they close in #21 (see there).
Acceptance: no `with_*` keys remain; touched role Molecules green.
Depends: 6 (interleave with 7–8, 19).

#### 21. Normalize shorthand, boolean, and string-boolean conditionals
- Convert `action:`/`debug: msg=` to mapping form
- `no/yes` → `false/true`.
- **v5:** `when:` no longer coerces `"true"/"false"` strings (any non-empty
  string is truthy) — inspect `when:`/`failed_when:`/`changed_when:` on string
  vars and add `| bool`. Silent change: found by inspection, not lint.
Prior art: [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
[#6235](https://github.com/dimagi/commcare-cloud/pull/6235) ("changes for
ansible upgrade 9.1.0/9.2.0") are the `include:` → `include_tasks:` +
module-shorthand rewrites — **close both here**. Their `include_tasks` portion
also satisfies the mechanical work noted in #20.
Acceptance: lint clean; no `when:` relies on implicit string→bool.

#### 22. Move arithmetic/concatenation inside Jinja (Ansible 6/core 2.13)
Arithmetic and concatenation are no longer allowed *outside* a Jinja template.
`'[1] + {{ [2] }}'` → `'{{ [1] + [2] }}'`. Grep `}}` adjacent to operators.
Acceptance: lint clean. Hard to fully detect on 4.10, so re-verify at 4→10.
Depends: 6.

#### 23. Harden conditional templating — highest-risk (the v8 + v12 arc)
- **v8/CVE-2023-5764** (core 2.15): embedded-template conditionals fail "unsafe"
  — reference untrusted values as plain Jinja vars, not embedded templates.
- **v12** (core 2.19): non-boolean `when:` is now an error — make conditionals
  explicitly boolean.
- **v12 native Jinja + trust model:** non-strings don't auto-stringify, only
  trusted strings render, and `omit` in loops drops immediately — flag dependents.
Build the candidate list from a repo-wide grep of `when:` / `failed_when:` /
`changed_when:` / `assert`.
Acceptance: triaged on 4.10; full verification only on core 2.15 & 2.19 (see #33).
Depends: 6.

#### 24. Fix ansible.cfg Galaxy URL
`old-galaxy.ansible.com` → `galaxy.ansible.com`.
Acceptance: galaxy installs resolve.

#### 25. Update custom plugins/modules for the newer core API
`module_utils._text` → `module_utils.common.text.converters`; `logging.warn` →
`warning`. Re-verify `cchq_aws_secret.py` and `library/*` against the target
`AnsibleModule`. Files: `plugins/inventory/csv.py`,
`plugins/lookup/cchq_aws_secret.py`, `library/*`.
Acceptance: import/run on target core; `test_csv_inventory.py` passes.

#### 26. Audit in-code `ansible.*` imports + version gate
Review CLI imports (`InventoryManager`, `DataLoader`, `VariableManager`,
vault/dumper helpers) for API drift; raise `min_ansible_version` (currently
`2.10.0`) on each step.
Acceptance: CLI imports succeed per target core; gate matches shipped version.

#### 27. Audit Ansible 13/core-2.20 behavior changes
Prefer `ansible_facts.*` over bare `ansible_*` facts (`INJECT_FACTS_AS_VARS`
flips to `False` in 2.24); the `failed_when` suppressed-error key is now
`failed_when_suppressed_exception`. `include_vars`: `extensions`/`ignore_files`
must be lists, not strings.
Acceptance: CLI imports succeed on each target core; verified at 12→14 (#34).

### Version bumps — sequential, after cleanup + a full test pass

#### 28. Ansible 4 → 10 (core 2.11→2.17)
The core/package bump. Ansible 10 is the highest reachable on Python 3.10.
Raise the `ansible` pin and `min_ansible_version`; re-pin collections to
core-2.17-compatible versions. Because all removed syntax — including the
monitoring roles (#12–16) — was fixed on 4.10 in the cleanup band, this is a
pure pin change with nothing left to break, and can be green and merged on its
own. The surviving-role re-pins (#29) and `gantsign.golang` (#30) are
version-coupled follow-ons that depend on this step but are *not* preconditions
of declaring it done.
Prior art: Dependabot [#6895](https://github.com/dimagi/commcare-cloud/pull/6895)
(ansible 4→10.7.0) and [#6444](https://github.com/dimagi/commcare-cloud/pull/6444)
(ansible-core 2.11→2.17.7) — **close both here** (they only touch the pin, so
can't merge until the cleanup band is done).
Acceptance: core 2.17 installs; `deploy_hq.yml` **and `deploy_prometheus.yml`**
syntax-check green on 2.17 (the latter proves #12–16 survived the bump);
full Molecule suite green on 10.
Fallback: bisect via 6/8 if failures are hard to localize.
Depends: 7–27 (incl. 12–16).

#### 29. Re-pin surviving standalone roles + re-test
Bump the still-maintained roles to their newest releases and re-test on core
2.17: `DavidWittman.redis`, `sansible.logstash`, the `andrewrothstein.*` SHAs
(couchdb, couchdb-cluster). Done here because verification needs the new core.
Acceptance: each touched role's Molecule (#6) green on 10; pins updated.
Depends: 28.

#### 30. Bump `gantsign.golang`
A live transitive dep (the collection's `agg_pushgateway_exporter` /
`airflow_exporter` use it to build Go exporters), so it can't be dropped.
Version-coupled: its latest (3.5.0) *requires core ≥2.17*, so it can only move
at/after the Ansible-10 bump (#28) — bump it here.
Acceptance: bumped and resolving on core 2.17; the two collection roles still
build their exporters.
Depends: 11, 28.

#### 31. (Optional) Swap vendored grafana + node_exporter to upstream collections
**Not a precondition of the Ansible-10 bump (#28)** — #15–16 already made these roles run on core
2.17 as repo-local vendored copies, so the stack is green on 10 without this.
This is a follow-on modernization that retires the vendored fork in favor of
maintained upstream collections (less to maintain forward). Their successors
floor at core 2.12 / 2.14, so it can only run post-Ansible-10. Do it when the fork
maintenance burden justifies it; skip it otherwise.
- Add `prometheus.prometheus` (`requires_ansible >=2.14.0,<=2.21.99`, for its
  `node_exporter` role) and `grafana.grafana` (`>=2.12.0,<3.0.0`) to
  `requirements.yml`. `prometheus.prometheus` pulls `community.general
  >=1.0.0`, satisfied by the pinned 7.4.0 — coordinate with #9.
- Compute and apply the `group_vars/` remap for the two roles: `grafana_*` →
  `grafana.grafana` vars, `node_exporter_*` →
  `prometheus.prometheus.node_exporter` vars (read from their upstream docs).
- Swap `deploy_prometheus.yml` refs from the repo-local roles →
  `grafana.grafana` and `prometheus.prometheus.node_exporter`, then delete the
  vendored grafana/node_exporter roles from `roles/`.
Prior art: [#6524](https://github.com/dimagi/commcare-cloud/pull/6524)
(the in-place node_exporter bump — its "0.21.5 → 0.21.5" no-op proved the
role is frozen) — **close here**, superseded by the #15–16 vendoring + this swap.
Acceptance: upstream collections installed and consumed; vendored
grafana/node_exporter roles deleted; monitoring Molecule/Vagrant stack
converges on core ≥2.14; metrics scrape end-to-end (see Glossary).
Depends: 15, 16, 28.

#### 32. Controller Python 3.10 → 3.12
3.12 is the latest Python explicitly supported by Ansible 10–12. Raise
`requires-python`, `.python-version`, CI matrix, base images; refresh `uv.lock`.
Optional: install + run tests on 3.14; if no blockers, jump to 3.14 here.
Acceptance: full suite green on Python 3.14 or 3.12 / Ansible 10.
Depends: 28 (with 29–30 green; 31 is optional and not required here).

#### 33. Ansible 10 → 12 (core 2.17→2.19)
Isolates the v12 templating overhaul, where #23 gets exercised and most breakage
is expected. Re-pin collections.
Prior art: Dependabot [#6758](https://github.com/dimagi/commcare-cloud/pull/6758)
(ansible 4→12.2.0) is the pin diff for this jump — **close it here** (rebased
onto the #28 result).
Acceptance: full suite green on 12 with zero templating/conditional errors.
Depends: 32, 23.

#### 34. Ansible 12 → 14 (core 2.19→2.21)
Confirm #27 changes and the per-collection `requires_ansible` gate (#9); final
collection re-pin. Runs on the #32 interpreter (3.12, or 3.14 if the #32
optional was taken).
Acceptance: full suite green on 14.
Depends: 33, 27.

#### 35. Controller Python 3.12 → 3.14
Skip if #32 already reached 3.14. Core 2.20+ are the first to officially support
Python 3.14. Raise `requires-python`, `.python-version`, CI matrix, base images;
refresh `uv.lock`. Verify own deps publish 3.14 wheels (esp. `cryptography`);
fall back to 3.13 if necessary.
Acceptance: full suite green.
Depends: 34.

### Validation & rollout

#### 36. Full-stack sign-off
End-to-end `deploy-stack` on Vagrant and the `tests/cloud/` Docker harness
against the final stack; idempotence pass.
Acceptance: clean monolith install + re-converge with zero unexpected changes.
Depends: 35, 5.

#### 37. Docs
New minimum Python, upgrade outcome, Molecule/Vagrant workflows,
changelog.
Acceptance: a new contributor can run the ansible test suite from docs alone.
Depends: 36.

---

## Glossary

- **Converge** (Ansible/Molecule): apply a role/playbook to a target host. A run
  *converges* when it completes with no errors. Paired with **idempotence** — a
  second run reports **zero changes** — this is the standard pass condition for
  Molecule scenarios (#5, #6) and full-stack re-runs (#36).
- **Scrape** (Prometheus): Prometheus' pull model — it periodically fetches the
  `/metrics` HTTP endpoint each exporter exposes (e.g. node_exporter on `:9100`).
  "Metrics scrape end-to-end" means the whole chain works: exporters are up and
  serving, Prometheus is configured to pull them, and each target registers as
  **up** on Prometheus' `/targets` page.

---

## Appendix A: Ansible/Python version matrix

Version → core → control-node Python (for sequencing):

| Ansible | core | Control Python | Status |
|--|--|--|--|
| 4  | 2.11 | 3.10 | Unmaintained (EOL) |
| 5  | 2.12 | 3.10-? | Unmaintained (EOL) |
| 6  | 2.13 | 3.10-? | Unmaintained (EOL) |
| 7  | 2.14 | 3.10-? | Unmaintained (EOL) |
| 8  | 2.15 | 3.10-? | Unmaintained (EOL) |
| 9  | 2.16 | 3.10-? | Unmaintained (EOL) |
| 10 | 2.17 | 3.10–3.12 | Unmaintained (EOL) |
| 11 | 2.18 | 3.11–3.13 | EOL Dec 2025 |
| 12 | 2.19 | 3.11–3.13 | EOL Dec 2025 |
| 13 | 2.20 | 3.12–3.14 | Current |
| 14 | 2.21 | 3.12–3.14 | Recently released as of June 2026? |

Support windows are *tested-against*, not enforced — `requires-python` is a
floor only (no upper-bound pin or runtime guard).

https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html

## Appendix B: Role dependency landscape

A previous contributor, pvisweswar, attempted this upgrade
([SAAS-14998](https://dimagi.atlassian.net/browse/SAAS-14998) /
[SAAS-16650](https://dimagi.atlassian.net/browse/SAAS-16650)) and stalled on
unmaintained standalone Galaxy roles. The artifacts are still open and may be
useful prior art:

- [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
  [#6235](https://github.com/dimagi/commcare-cloud/pull/6235) ("changes for
  ansible upgrade 9.1.0 / 9.2.0", branches `ansible/upgrade`,
  `ansible/upgrade-9.2.0`) — the `include:` → `include_tasks:` and
  module-shorthand cleanups (overlaps #20–21 here).
- [#6520](https://github.com/dimagi/commcare-cloud/pull/6520) /
  [#6524](https://github.com/dimagi/commcare-cloud/pull/6524) ("Upgrading
  Ansible dependency for cloudalchemy.prometheus / node_exporter",
  [SAAS-16650](https://dimagi.atlassian.net/browse/SAAS-16650)) — the attempt to
  move the monitoring roles forward. #6524 bumps node_exporter "0.21.5 → 0.21.5"
  — a no-op, because the role is frozen at its final release. That dead end is
  the core finding below.

**Maintenance audit of every dependency in `ansible/requirements.yml`** (checked
against GitHub archived flag + last push, June 2026):

| Dependency | Repo | State | Last activity | Verdict |
|--|--|--|--|--|
| `cloudalchemy.prometheus` | cloudalchemy/ansible-prometheus | **ARCHIVED 2023-03** | rel 4.0.0 (2021-05) | **DEAD** → vendored into `dimagi.commcare_prometheus` on 4.10 (#12, released/adopted in #14) |
| `cloudalchemy.alertmanager` | cloudalchemy/ansible-alertmanager | **ARCHIVED 2023-03** | rel 0.19.1 (2020-09) | **DEAD** → vendored into `dimagi.commcare_prometheus` on 4.10 (#13, released/adopted in #14) |
| `cloudalchemy.grafana` | cloudalchemy/ansible-grafana | **ARCHIVED 2023-05** | rel 0.17.0 (2020-03) | **DEAD** → vendored repo-local on 4.10 (#15; fixes 8× `include:` + 1× `warn:`); optional upstream swap → `grafana.grafana` post-Ansible-10 (#31) |
| `cloudalchemy.node_exporter` | cloudalchemy/ansible-node-exporter | **ARCHIVED 2023-03** | rel 2.0.0 (2021-04) | **DEAD** → vendored repo-local on 4.10 (#16; fixes 1× `warn:` in `preflight.yml`); optional upstream swap → `prometheus.prometheus.node_exporter` post-bump (#31, renamed `node-exporter`→`node_exporter`) |
| `bdellegrazie.postgres_exporter` | bdellegrazie/ansible-role-postgres_exporter | stale | 2022-12 | **transitive dep** of `dimagi.commcare_prometheus.postgres_exporter` (its `meta` requires it) — not orphaned; stale (2022). Keep/re-test (#11) |
| `gantsign.golang` | gantsign/ansible-role-golang | active | rel 3.5.0 (2025-04) | **transitive dep** of the collection's `agg_pushgateway_exporter` + `airflow_exporter` (build Go exporters) — not orphaned; **version-coupled** (latest *requires* core ≥2.17), bump at #30 (#11) |
| `DavidWittman.redis` | DavidWittman/ansible-redis | semi-active | rel 1.2.12 (2024-01), 57 open issues | re-test on target core; bump if needed (#29) |
| `sansible.logstash` | sansible/logstash | low activity | v2.4.4 | re-test on target core (#29) |
| `andrewrothstein.couchdb` | andrewrothstein/ansible-couchdb | maintained | 2024-06 (SHA-pinned, no releases) | re-test; keep SHA pin (#29) |
| `andrewrothstein.couchdb-cluster-*` | dimagi/ansible-couchdb-cluster | Dimagi fork | 2023-03 (SHA-pinned) | we own it — fix forward if it breaks (#29) |
| `tmpreaper` (`ANXS/tmpreaper`) | ANXS/tmpreaper | **DEAD** | **2017-07** | trivial role — vendor or replace (#17) |
| `ansible-logrotate` | nickhammond/ansible-logrotate | **DEAD** | **2018-10** (v0.0.5) | trivial role — vendor or replace (#18) |
| `dimagi.commcare_prometheus` | dimagi/commcare-prometheus | Dimagi, stale | rel 0.1.10 (**2020-10**) | **cross-repo work required** (#12–14) — see below |
| `dimagi.commcare_logstash` | dimagi/commcare-logstash | Dimagi | 2022-01 (0.9.5) | re-test; we own it (#9) |
| `community.general` | (collection) | active | pinned 7.4.0 | bump in lockstep with core (#9) |

**Why the cloudalchemy roles can't just be deleted:**
`deploy_prometheus.yml` imports `dimagi.commcare_prometheus.prometheus` and
`...alertmanager`, and those vendored roles' `meta/main.yml` declare
`dependencies: [cloudalchemy.prometheus]` / `[cloudalchemy.alertmanager]`.
Grafana and node-exporter are imported from cloudalchemy **directly** in the
playbook (`cloudalchemy.grafana`, `cloudalchemy.node-exporter` — note the legacy
hyphen). So two of the four archived roles (prometheus, alertmanager) are
pulled in *transitively through a separate, 2020-vintage Dimagi-owned
collection repo* — those are removed on 4.10 in #12–14 by self-containing that
collection (editing `dimagi/commcare-prometheus` in #12–13, then releasing +
bumping the pin in #14).
The other two (grafana, node_exporter) are direct refs. Their maintained
upstream successors floor at core 2.12 / 2.14, so they *cannot* be adopted on
4.10. To keep the bump (#28) free of monitoring breakage and independently
mergeable, #15–16 instead vendor them as repo-local roles and fix their removed
syntax cross-version-safe on 4.10 (the same treatment #12–14 give
prometheus/alertmanager, and #17/#18 give tmpreaper/logrotate). The upstream
cutover (#31) then becomes an *optional* post-bump cleanup, not a bump
precondition. After #12–16, no `cloudalchemy.*` pin or ref survives into the
bump.

**Successor target versions** for the optional #31 swap (both admit the v14
ceiling, confirmed via `meta/runtime.yml`): `prometheus.prometheus`
`requires_ansible >=2.14.0,<=2.21.99` (bundles prometheus, alertmanager,
node_exporter, *and* postgres_exporter roles); `grafana.grafana`
`requires_ansible >=2.12.0,<3.0.0`. The 2.12 / 2.14 floors are why these can't
be adopted on 4.10 — hence the #15–16 vendoring steps.

---

## Notes

- **Depends** should be encoded as ticket links in the ticket description.
- **Acceptance** should include ticket links where appropriate.
- **Verification layers:** lint + syntax (CI, #3); Molecule converge/idempotence
  (#5, #6); Vagrant + `tests/cloud/` full-stack (#4, #36); pytest CLI suite on
  the target Python/core.
- **Local constraint:** ansible is never run on the dev machine — bumps are
  validated in CI and on Vagrant/Docker targets only.
- **Open questions:** confirm...
  - 14.x has a stable collection set at execution.
  - whether `community.general 7.4.0` needs bumping in lockstep with the cores.
  - that we need to maintain prometheus/grafana automation at all.
  - whether `prometheus.prometheus` / `grafana.grafana` defaults differ enough
    from the cloudalchemy roles to need group_vars remapping beyond the #31
    cutover's estimate.
  - add an Ansible 11 stop only if the SSH/Windows or docker-default changes
    prove relevant (unlikely — commcare-cloud targets Linux).
