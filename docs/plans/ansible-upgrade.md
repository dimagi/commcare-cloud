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
(`deploy_hq.yml`, `deploy_postgres.yml`, the `restart_*` / `deploy_citusdb` /
`deploy_proxy` set, etc.) get neither. That coverage gap is the upgrade's
biggest risk, so the test tickets come first.

Sequence: clean up deprecations and build a test safety net first, then step
through versions. The interpreter may move in two hops: **3.10 → 3.12** (spans
Ansible 10–12), then **3.12 → 3.14** at the 12 → 14 jump (or one hop if 3.14
tests pass early — #28 optional).

### Highest-risk changes (v5–v14)

1. **Templating/conditional strictness**, peaking at core 2.19: string-boolean
   conditionals (v5), arithmetic outside `{{ }}` (v6), embedded-template
   conditionals (v8/CVE-2023-5764), and non-boolean `when:` as an error + native
   Jinja + inverted trust model (v12). → tickets 19–21.
2. **Collection removals** in every major version. Pin and explicitly install
   collectinos that were removed from Ansible. → #10–13.

---

## Backlog

"Depends" = ticket numbers. 1–5 are housekeeping; 6–9 build the test safety net;
10–25 are version-agnostic cleanup (10–16 dependency work; 17–25 deprecation
edits) and parallelize within their bands; 26–33 are mostly sequential version
bumps + rollout. Every cleanup ticket (10–25) must leave the tree green on 4.10
on its own, so that each bump (26/29/30) is a pin change with nothing left to fix.

### Housekeeping — independent, do first

#### 1. Drop `gitpython`
Used once in `ops_tool.py` (`git.Repo(search_parent_directories=True)`); replace
with a `subprocess` git call and remove from `pyproject.toml`/`uv.lock`.
Acceptance: repo root still resolves; dep gone; tests green.

#### 2. Remove stale Ubuntu 18.04 references
18.04 is unsupported. Search `18.04|bionic`.
Delete `ansible_distribution_version == '18.04'` branches.
Acceptance: none remain; 22.04 path unaffected.

#### 3. Remove the CitusDB automation
CitusDB is no longer used; remove its install/management automation.
- Delete `deploy_citusdb.yml` and the `roles/citusdb/` role.
- Remove the citus import/host blocks from `deploy_db.yml` and the `!citusdb`
  exclusions in `deploy_postgres.yml` / `wipe_postgres.yml` /
  `setup_pg_standby.yml` and the `pg_upgrade_*` playbooks.
- Untangle the PostgreSQL coupling (the non-trivial part): the
  `citusdb_master` / `citusdb_worker` routing in
  `environment/schemas/postgresql.py`, the citus worker ACL block in
  `roles/postgresql_base/templates/pg_hba.conf.j2`, the
  `allow_direct_citusdb_access` default, and the citus pgbouncer vars
  (`roles/citusdb/vars/pgbouncer_workers.yml` + `roles/pgbouncer` routing).
- Drop `group_vars/citusdb_master.yml` / `citusdb_worker.yml`, the `Citusdb`
  service class in `commands/ansible/service.py`, the citus monitoring entries
  (`roles/datadog/defaults/main.yml`, `monitors/pg_replication_delay.yml`), and
  the citus host in `environments/development/postgresql.yml`.
- The `citusdb` / `citusdb_master` / `citusdb_worker` inventory groups become
  unused — drop them from example environments where present.
- Remove CitusDB docs (`docs/source/services/postgresql/upgrade_citusdb.rst`;
  trim citus from `postgresql.rst`) and publish a changelog entry.
Acceptance: no `citus` references remain; `deploy_postgres` / `deploy_db` and the
postgres Molecule (#9) are green without them; `deploy-stack` unaffected.

#### 4. Remove the RabbitMQ automation
The Celery broker has migrated to Redis (changelog `0096`; RabbitMQ support ended
2026-06-01), so RabbitMQ is no longer used — remove its automation.
- Delete `deploy_rabbitmq.yml` and the `roles/rabbitmq/` role.
- Remove the rabbitmq import/host blocks from `deploy_db.yml` and the rabbitmq
  plays in `ping.yml`, `stop_servers.yml`, `status_check.yml`, and
  `deploy_cloudwatch_logs.yml`.
- Drop `group_vars/rabbitmq.yml`, the `RabbitMq` service class in
  `commands/ansible/service.py`, the `rabbit` forward-port in
  `inventory_lookup.py`, the rabbitmq datadog integration
  (`roles/datadog/defaults/main.yml` + `templates/rabbitmq.yaml.j2`), the Celery
  Flower AMQP wiring (`supervisor_celery_flower.conf.j2`), and the rabbitmq
  alias in `roles/common/templates/etc_aliases.j2`.
- The `rabbitmq` inventory group becomes unused — drop the `[rabbitmq:children]`
  blocks from the example/inventory templates and the `AMQP_*` / `OLD_AMQP_*`
  env wiring from example environments.
- Remove RabbitMQ docs (`docs/source/services/rabbitmq/*`) and the
  commcare-ports / firefighting references; publish a changelog entry.
- **Caveat:** confirm no live environment still points `BROKER_URL` at AMQP
  before removing — the localsettings broker wiring is shared with the (kept)
  Redis broker, so touch only the AMQP-specific paths.
Acceptance: no rabbitmq/AMQP install references remain; `deploy-stack` and Celery
(on the Redis broker) are unaffected; `test_getinventory.py` is updated.

#### 5. Remove the Prometheus install automation
Remove `deploy_prometheus.yml` and all dependencies used only by it from
`requirements.yml`.
- Check references to `prometheus` / `grafana` / `alertmanager` /
  `node_exporter` / `bdellegrazie.postgres_exporter` / `gantsign.golang`.
- Check relevance of `group_vars/prometheus.yml`, `group_vars/alertmanager.yml`,
  `environment/schemas/prometheus.py` + its wiring in `environment/main.py`.
- The `prometheus`/`alertmanager`/`grafana`/`prometheus_proxy` inventory groups
  become unused — drop them from example environments where present.
- Remove Prometheus installation docs.
- Keep app-level, gated by `prometheus_monitoring_enabled`, independent of the
  server install: the `localsettings.py.j2` metrics-provider injection;
  `supervisor_prometheus.conf.j2` + `django_bash_runner.sh.j2`; the
  `PROMETHEUS_MULTIPROC_DIR` / `PROMETHEUS_PUSHGATEWAY_HOST` env wiring in the
  `commcarehq` role tasks (webworkers/pillowtop/management_commands/celery); the
  gated "Prometheus Supervisor Config" / "Prometheus Django runner" plays in
  `deploy_commcarehq.yml`; and `prometheus_monitoring_enabled` / `metrics_home`
  in `group_vars/all.yml`. HQ still exposes `/metrics`; Prometheus scrapes it.
- Publish a change log entry: while Prometheus is still supported for
  monitoring, commcare-cloud will no longer install the Prometheus monitoring
  stack. Operators who want Prometheus/Grafana can stand it up themselves
  following Prometheus' own docs.
Prior art — both **close here**, superseded by removal:
[#6520](https://github.com/dimagi/commcare-cloud/pull/6520) /
[#6524](https://github.com/dimagi/commcare-cloud/pull/6524) — the cloudalchemy
upgrade attempts.
Acceptance: `deploy_prometheus.yml` et al are gone; `test_install.py` and the
monitoring docs are updated; `deploy-stack` is unaffected; and with
`prometheus_monitoring_enabled` still settable + set to `True`, the
`deploy_commcarehq` path renders localsettings + supervisor configs
(syntax/Molecule green with the flag both on and off).
Decision thread:
https://dimagi.slack.com/archives/CNQ636095/p1781277055592099?thread_ts=1781210489.586889&cid=CNQ636095

### Safety net — build verification before touching versions

#### 6. CI lint + syntax for all playbooks
Add `ansible-lint` (dev dep) and extend `--syntax-check` to cover the
top-level playbooks *not* reached by the existing `deploy_stack.yml` check —
`deploy_hq.yml`, `deploy_postgres.yml`, the `restart_*` / `deploy_proxy` set,
etc. (`deploy_stack.yml` and its ~18 imports are already syntax-checked by
`.tests/tests.sh`; `deploy_prometheus.yml` is excluded — it's being removed in
#5); capture existing violations as a baseline. Full FQCN module normalization
is low-priority baseline debt (short names resolve fine; collection moves are
handled by #10–11).
Acceptance: new non-blocking `lint.yml` fails on new violations; green on day one.

#### 7. Refresh Vagrant harness to 22.04
`Vagrantfile` is `ubuntu/bionic64` (18.04); upgrade it, verify provisioning,
document the local full-stack flow.
Acceptance: `vagrant up` + `deploy-stack` completes on 22.04 on current Ansible.

#### 8. Molecule scaffolding + one reference role
Add Molecule (docker driver) with a shared base config and a worked example for
one simple role (e.g. `swap` or `logrotate`, which already has a `tests/` stub).
Wire a Molecule job into CI. Document "how to add a Molecule scenario." Keep
test code separate from production code.
Acceptance: `molecule test` converge + idempotence green locally and in CI on 22.04.

#### 9. Molecule coverage for critical roles
Add Molecule converge/idempotence scenarios for the operationally critical,
untested roles: postgresql(_base), pgbouncer, couchdb2, kafka, redis,
elasticsearch, nginx, proxy/haproxy. Likely one Jira ticket per role/group.
Acceptance: each converges twice with no changes; basic service-up asserts.
Depends: 8.

### Dependency work — collections + roles, version-agnostic, run on 4.10

#### 10. Adopt `community.postgresql` (declare + migrate `postgresql_*`)
Add `community.postgresql` to `requirements.yml`, then FQCN-ify
`postgresql_user/db/privs/set/query` and drop `encrypted:` (removed in core 2.15).
Files:
- `roles/postgresql_base/tasks/set_up_dbs.yml`
- `roles/postgresql_base/tasks/main.yml`
- any playbook needing a `collections:` entry.
Acceptance: `ansible-galaxy install -r` resolves the collection; Molecule
postgres (#9) + syntax clean.
Depends: ideally 9.

#### 11. Adopt `ansible.posix`
Add `ansible.posix` to `requirements.yml`, then FQCN-ify `synchronize` /
`authorized_key` in `roles/deploy_hq/tasks/staticfiles_*` and
`roles/setup_auth_keys.yml`.
Acceptance: collection installs; refs resolve to `ansible.posix.*`; lint clean.

#### 12. Audit `community.general` + `dimagi.commcare_logstash`
Decide whether `community.general 7.4.0` is still required and at what version,
and confirm `dimagi.commcare_logstash` loads on the target cores. (The other
Dimagi collection, `dimagi.commcare_prometheus`, is removed in #5, so it drops
out of this audit.) Record each collection's `requires_ansible` and confirm it
admits core 2.21 (v14 excludes incompatible collections by default).
Acceptance: necessity decision recorded; a compat-matrix entry per surviving
collection.

#### 13. Removed-collection audit (collections dropped v5–v14)
The repo uses short module names (FQCN is ~6 tasks total), so grep the *short
module names* of every collection removed from the `ansible` package across
v5–v14 (per each version's changelog). Pin and explicitly install any still in
use.
Acceptance: nothing in-use silently disappears at any version step; pins added.

#### 14. Standalone-role maintenance audit; drop orphaned roles
Use the Appendix B matrix as the baseline: for each *role* in `requirements.yml`
record archived flag, last activity, target-core compatibility. The monitoring
roles (`cloudalchemy.*`, plus the transitive `gantsign.golang` /
`bdellegrazie.postgres_exporter`) are removed wholesale in #5, so this ticket
covers the survivors: `DavidWittman.redis`, `sansible.logstash`, the
`andrewrothstein.*` couchdb roles.
Acceptance: role compat matrix complete; orphaned pins removed or justified.

#### 15. Vendor or replace `tmpreaper`
Abandoned but trivial (`ANXS/tmpreaper`, dead since 2017); used in several
playbooks. Risk is removed syntax (`with_items`, bare `warn:`, string-bool
`when:`) failing on the target core. Fork into the repo as a local role under
`roles/` (preferred — a maintainable copy we can fix forward) or replace with a
few inline tasks; re-point `requirements.yml` / refs.
Acceptance: resolves to a repo-local role (or inline tasks); no abandoned pin
remains; touched-role Molecule green on the target core.

#### 16. Vendor or replace `ansible-logrotate`
Same approach as #15 (`nickhammond`, dead since 2018). Heavily used — it's a
`meta` dependency of `common`, so nearly every host pulls it; test broadly.
Acceptance: resolves to a repo-local role (or inline tasks); no abandoned pin
remains; `common`-dependent role Molecules green on the target core.

### Deprecation cleanup — version-agnostic, run on 4.10

#### 17. Remove `warn:` on command/shell
~15, mostly `ping.yml`; removed in core 2.14.
Acceptance: none remain; lint clean.

#### 18. Convert `with_*` to `loop:`
Largest change: ~125 across ~21 files. Add appropriate filters/`lookup`.
Mechanical; split on playbook and role.
Prior art: [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
[#6235](https://github.com/dimagi/commcare-cloud/pull/6235) carry the same kind
of mechanical loop/`include_tasks` rewrite; they close in #19.
Acceptance: no `with_*` keys remain; touched role Molecules green.
Depends: 9 (interleave with 10–11, 17).

#### 19. Normalize shorthand, boolean, and string-boolean conditionals
- Convert `action:`/`debug: msg=` to mapping form
- `no/yes` → `false/true`.
- **v5:** `when:` no longer coerces `"true"/"false"` strings (any non-empty
  string is truthy) — inspect `when:`/`failed_when:`/`changed_when:` on string
  vars and add `| bool`. Silent change: found by inspection, not lint.
Prior art: [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
[#6235](https://github.com/dimagi/commcare-cloud/pull/6235) ("changes for
ansible upgrade 9.1.0/9.2.0") are the `include:` → `include_tasks:` +
module-shorthand rewrites — **close both here**. Their `include_tasks` portion
also satisfies the mechanical work noted in #18.
Acceptance: lint clean; no `when:` relies on implicit string→bool.

#### 20. Move arithmetic/concatenation inside Jinja (Ansible 6/core 2.13)
Arithmetic and concatenation are no longer allowed *outside* a Jinja template.
`'[1] + {{ [2] }}'` → `'{{ [1] + [2] }}'`. Grep `}}` adjacent to operators.
Acceptance: lint clean. Hard to fully detect on 4.10, so re-verify at 4→10.
Depends: 9.

#### 21. Harden conditional templating — highest-risk (the v8 + v12 arc)
- **v8/CVE-2023-5764** (core 2.15): embedded-template conditionals fail "unsafe"
  — reference untrusted values as plain Jinja vars, not embedded templates.
- **v12** (core 2.19): non-boolean `when:` is now an error — make conditionals
  explicitly boolean.
- **v12 native Jinja + trust model:** non-strings don't auto-stringify, only
  trusted strings render, and `omit` in loops drops immediately — flag dependents.
Build the candidate list from a repo-wide grep of `when:` / `failed_when:` /
`changed_when:` / `assert`.
Acceptance: triaged on 4.10; full verification only on core 2.15 & 2.19 (see #29).
Depends: 9.

#### 22. Fix ansible.cfg Galaxy URL
`old-galaxy.ansible.com` → `galaxy.ansible.com`.
Acceptance: galaxy installs resolve.

#### 23. Update custom plugins/modules for the newer core API
`module_utils._text` → `module_utils.common.text.converters`; `logging.warn` →
`warning`. Re-verify `cchq_aws_secret.py` and `library/*` against the target
`AnsibleModule`. Files: `plugins/inventory/csv.py`,
`plugins/lookup/cchq_aws_secret.py`, `library/*`.
Acceptance: import/run on target core; `test_csv_inventory.py` passes.

#### 24. Audit in-code `ansible.*` imports + version gate
Review CLI imports (`InventoryManager`, `DataLoader`, `VariableManager`,
vault/dumper helpers) for API drift; raise `min_ansible_version` (currently
`2.10.0`) on each step.
Acceptance: CLI imports succeed per target core; gate matches shipped version.

#### 25. Audit Ansible 13/core-2.20 behavior changes
Prefer `ansible_facts.*` over bare `ansible_*` facts (`INJECT_FACTS_AS_VARS`
flips to `False` in 2.24); the `failed_when` suppressed-error key is now
`failed_when_suppressed_exception`. `include_vars`: `extensions`/`ignore_files`
must be lists, not strings.
Acceptance: CLI imports succeed on each target core; verified at 12→14 (#30).

### Version bumps — sequential, after cleanup + a full test pass

#### 26. Ansible 4 → 10 (core 2.11→2.17)
The core/package upgrade. Ansible 10 is the highest reachable on Python 3.10.
Raise the `ansible` pin and `min_ansible_version`; re-pin collections to
core-2.17-compatible versions.
Prior art: Dependabot [#6895](https://github.com/dimagi/commcare-cloud/pull/6895)
(ansible 4→10.7.0) and [#6444](https://github.com/dimagi/commcare-cloud/pull/6444)
(ansible-core 2.11→2.17.7) — **close both here** (they only touch the pin, so
can't merge until the cleanup band is done).
Acceptance: core 2.17 installs; `deploy_hq.yml` syntax-check green; full
Molecule suite green on Ansible 10.
Fallback: bisect via 6/8 if failures are hard to localize.
Depends: 10–25

#### 27. Re-pin surviving standalone roles + re-test
Bump the still-maintained roles to their newest releases and re-test on core
2.17: `DavidWittman.redis`, `sansible.logstash`, the `andrewrothstein.*` SHAs
(couchdb, couchdb-cluster). Done here because verification needs the new core.
Acceptance: each touched role's Molecule (#9) green on Ansible 10; pins updated.
Depends: 26.

#### 28. Controller Python 3.10 → 3.12
3.12 is the latest Python explicitly supported by Ansible 10–12. Raise
`requires-python`, `.python-version`, CI matrix, base images; refresh `uv.lock`.
Optional: install + run tests on 3.14; if no blockers, jump to 3.14 here.
Acceptance: full suite green on Python 3.14 or 3.12 / Ansible 10.
Depends: 26 (with 27 green).

#### 29. Ansible 10 → 12 (core 2.17→2.19)
Isolates the v12 templating overhaul, where #21 gets exercised and most breakage
is expected. Re-pin collections.
Prior art: Dependabot [#6758](https://github.com/dimagi/commcare-cloud/pull/6758)
**close it here**.
Acceptance: full suite green on 12 with zero templating/conditional errors.
Depends: 28, 21.

#### 30. Ansible 12 → 14 (core 2.19→2.21)
Confirm #25 changes and the per-collection `requires_ansible` gate (#12); final
collection re-pin. Runs on the #28 interpreter (3.12, or 3.14 if the #28
optional was taken).
Acceptance: full suite green on 14.
Depends: 29, 25.

#### 31. Controller Python 3.12 → 3.14
Skip if #28 already reached 3.14. Core 2.20+ are the first to officially support
Python 3.14. Raise `requires-python`, `.python-version`, CI matrix, base images;
refresh `uv.lock`. Verify own deps publish 3.14 wheels (esp. `cryptography`);
fall back to 3.13 if necessary.
Acceptance: full suite green.
Depends: 30.

### Validation & rollout

#### 32. Full-stack sign-off
End-to-end `deploy-stack` on Vagrant and the `tests/cloud/` Docker harness
against the final stack; idempotence pass.
Acceptance: clean monolith install + re-converge with zero unexpected changes.
Depends: 31, 8.

#### 33. Docs
New minimum Python, upgrade outcome, Molecule/Vagrant workflows, changelog.
Acceptance: a new contributor can run the ansible test suite from docs alone.
Depends: 32.

---

## Glossary

- **Converge** (Ansible/Molecule): apply a role/playbook to a target host. A run
  *converges* when it completes with no errors. Paired with **idempotence** — a
  second run reports **zero changes** — this is the standard pass condition for
  Molecule scenarios (#8, #9) and full-stack re-runs (#32).
- **Scrape** (Prometheus): Prometheus' pull model — it periodically fetches the
  `/metrics` HTTP endpoint a target exposes. After #5, HQ still exposes its
  metrics endpoint (the kept app-level integration), but the Prometheus server
  that scrapes it is operator-managed, not installed by commcare-cloud.

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
unmaintained standalone Galaxy roles — chiefly the monitoring stack. The
artifacts are still open and may be useful prior art:

- [#6209](https://github.com/dimagi/commcare-cloud/pull/6209) /
  [#6235](https://github.com/dimagi/commcare-cloud/pull/6235) ("changes for
  ansible upgrade 9.1.0 / 9.2.0", branches `ansible/upgrade`,
  `ansible/upgrade-9.2.0`) — the `include:` → `include_tasks:` and
  module-shorthand cleanups (overlaps #18–19 here).
- [#6520](https://github.com/dimagi/commcare-cloud/pull/6520) /
  [#6524](https://github.com/dimagi/commcare-cloud/pull/6524) ("Upgrading
  Ansible dependency for cloudalchemy.prometheus / node_exporter",
  [SAAS-16650](https://dimagi.atlassian.net/browse/SAAS-16650)) — the attempt to
  move the monitoring roles forward. #6524 bumps node_exporter "0.21.5 → 0.21.5"
  — a no-op, because the role is frozen at its final release. That dead end is
  what motivates removing the monitoring install outright (#5) instead of
  upgrading it.

**Maintenance audit of every dependency in `ansible/requirements.yml`** (checked
against GitHub archived flag + last push, June 2026):

| Dependency | Repo | State | Last activity | Verdict |
|--|--|--|--|--|
| `cloudalchemy.prometheus` | cloudalchemy/ansible-prometheus | **ARCHIVED 2023-03** | rel 4.0.0 (2021-05) | **DEAD** → removed with the Prometheus install automation (#5) |
| `cloudalchemy.alertmanager` | cloudalchemy/ansible-alertmanager | **ARCHIVED 2023-03** | rel 0.19.1 (2020-09) | **DEAD** → removed (#5) |
| `cloudalchemy.grafana` | cloudalchemy/ansible-grafana | **ARCHIVED 2023-05** | rel 0.17.0 (2020-03) | **DEAD** → removed (#5) |
| `cloudalchemy.node_exporter` | cloudalchemy/ansible-node-exporter | **ARCHIVED 2023-03** | rel 2.0.0 (2021-04) | **DEAD** → removed (#5) |
| `bdellegrazie.postgres_exporter` | bdellegrazie/ansible-role-postgres_exporter | stale | 2022-12 | transitive dep of `dimagi.commcare_prometheus.postgres_exporter` — removed with it (#5) |
| `gantsign.golang` | gantsign/ansible-role-golang | active | rel 3.5.0 (2025-04) | transitive dep of the collection's Go-exporter roles — removed with it (#5); only the monitoring stack used it |
| `dimagi.commcare_prometheus` | dimagi/commcare-prometheus | Dimagi, stale | rel 0.1.10 (**2020-10**) | only consumed by `deploy_prometheus.yml` → removed (#5) |
| `DavidWittman.redis` | DavidWittman/ansible-redis | semi-active | rel 1.2.12 (2024-01), 57 open issues | re-test on target core; bump if needed (#27) |
| `sansible.logstash` | sansible/logstash | low activity | v2.4.4 | re-test on target core (#27) |
| `andrewrothstein.couchdb` | andrewrothstein/ansible-couchdb | maintained | 2024-06 (SHA-pinned, no releases) | re-test; keep SHA pin (#27) |
| `andrewrothstein.couchdb-cluster-*` | dimagi/ansible-couchdb-cluster | Dimagi fork | 2023-03 (SHA-pinned) | we own it — fix forward if it breaks (#27) |
| `tmpreaper` (`ANXS/tmpreaper`) | ANXS/tmpreaper | **DEAD** | **2017-07** | trivial role — vendor or replace (#15) |
| `ansible-logrotate` | nickhammond/ansible-logrotate | **DEAD** | **2018-10** (v0.0.5) | trivial role — vendor or replace (#16) |
| `dimagi.commcare_logstash` | dimagi/commcare-logstash | Dimagi | 2022-01 (0.9.5) | re-test; we own it (#12) |
| `community.general` | (collection) | active | pinned 7.4.0 | bump in lockstep with core (#12) |

---

## Notes

- **Depends** should be encoded as ticket links in the ticket description.
- **Acceptance** should include ticket links where appropriate.
- **Verification layers:** lint + syntax (CI, #6); Molecule converge/idempotence
  (#8, #9); Vagrant + `tests/cloud/` full-stack (#7, #32); pytest CLI suite on
  the target Python/core.
- **Local constraint:** ansible is never run on the dev machine — bumps are
  validated in CI and on Vagrant/Docker targets only.
- **Open questions:** confirm...
  - 14.x has a stable collection set at execution.
  - whether `community.general 7.4.0` needs bumping in lockstep with the cores.
  - ~~whether we need to maintain prometheus/grafana automation at all~~ —
    **resolved:** no; #5 removes it and documents operator-managed Prometheus.
  - add an Ansible 11 stop only if the SSH/Windows or docker-default changes
    prove relevant (unlikely — commcare-cloud targets Linux).
