# Molecule tests

Molecule tests for roles under `src/commcare_cloud/ansible/roles/` live
here, one directory per role/scenario pair:

```
tests/molecule/<role>-<scenario>/
    molecule.yml
    converge.yml
    prepare.yml   (optional)
    verify.yml
```

## Running scenarios

```sh
./tests/molecule/run.sh [ROLE [SCENARIO]]
```

## Adding a new scenario for a role

```sh
./tests/molecule/init.sh ROLE [SCENARIO]
```

## Container choice

The `containers` molecule driver is used, which picks whichever of
`podman`/`docker` is available. If your container engine is rootless — check
with `podman info`/`docker info` — that matters for two things role authors
should know about:

- **Anything needing real root against the host kernel** (enabling swap,
  non-namespaced sysctls, raw device access, etc.) **fails in a rootless
  container**, even with `privileged: true` — its "root" is a mapped
  unprivileged host UID. Work around it in the scenario (e.g. stub the
  binary in `prepare.yml`), not the role.
- **Non-namespaced sysctls** can be written to their config file, but the live
  `/proc/sys` value never actually changes, so `ansible.posix.sysctl` reports
  `changed` every run, breaking idempotence. Fix with `module_defaults`
  (`sysctl_set`/`reload: false`) on the scenario's `include_role` task.

The platform image is `docker.io/geerlingguy/docker-ubuntu2204-ansible`, rather
than a generic systemd/Ubuntu image. It's built specifically for
Ansible/Molecule testing — systemd, `sudo`, and `python3` pre-configured.

## Minimizing Molecule warnings

Molecule warns if a scenario doesn't configure a `cleanup` or `side_effect`
playbook (among others). Point the unused step at the shared no-op in
`tests/molecule/lib/stub.yml` to avoid warnings:

```yaml
provisioner:
  name: ansible
  playbooks:
    cleanup: ../lib/stub.yml
    side_effect: ../lib/stub.yml
```

If a role has no galaxy roles/collections to install, keep the dependency
manager disabled, but use `name: shell` rather than `name: galaxy` so it only
emits one warning instead of two:

```yaml
dependency:
  name: shell
  command: ''
  enabled: false
```

## About the directory structure

Molecule assumes one role per repo, and by default puts each role's scenarios
beside its source files. commcare-cloud, however, keeps all tests under the
`tests` directory at the repo root, so scenarios live in `tests/molecule/`.
Molecule also requires scenario names to be unique with no notion of "role" so
the role name is folded into the scenario directory name itself.
