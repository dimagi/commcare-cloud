# Design: `ec2_instance_state` Ansible module

**Date**: 2026-04-13
**Branch**: `ap/ansible-ec2-restart-module`
**Author**: Amit Phulera

## Goal

Provide a custom Ansible module for commcare-cloud that can start, stop, restart, and describe EC2 instances by instance ID. Support common ops scenarios such as rebooting an instance after maintenance, or temporarily stopping a non-prod host to save cost.

## Non-goals

- Terminating or launching instances. Lifecycle creation/destruction is owned by Terraform.
- Resolving instance IDs from inventory inside the module. The module is a pure AWS primitive; the playbook layer resolves IDs from inventory hostvars (`ec2_instance_id`).
- Multi-region operations in a single call. One region per invocation.

## Module identity & location

- **File**: `src/commcare_cloud/ansible/library/ec2_instance_state.py`
- **Module name**: `ec2_instance_state`
- **Convention**: Single-file Python module following the existing pattern in `src/commcare_cloud/ansible/library/` (alongside `clean_releases.py`, `setup_virtualenv.py`, `git_setup_release.py`). Includes `DOCUMENTATION`, `EXAMPLES`, `RETURN`, `main()` using `AnsibleModule`.
- **Dependency**: `boto3` (already pinned at 1.39.3 in `requirements.txt`). Imported lazily; module fails with a clear error if absent.
- **Execution context**: Designed for `delegate_to: localhost`. AWS credentials live on the controller, and the target host may itself be the one being stopped — running the module on it would be self-defeating.

## Parameters

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `instance_ids` | list[str] | yes | — | EC2 instance IDs (e.g. `i-0abc123...`). Must be non-empty. |
| `state` | str | yes | — | One of `started`, `stopped`, `restarted`, `described`. |
| `region` | str | no | `os.environ.get('AWS_REGION')` | AWS region. Falls back to the `AWS_REGION` env var, which commcare-cloud already exports when launching ansible (`src/commcare_cloud/environment/secrets/backends/aws_secrets/main.py:42-57`). Module fails with a clear message if neither is set. Mirrors the pattern in `src/commcare_cloud/ansible/plugins/lookup/cchq_aws_secret.py:41`. |
| `wait` | bool | no | `true` | Block until target state reached. Ignored for `described`. |
| `wait_timeout` | int | no | `600` | Seconds. Applied per state-transition (`restarted` allows up to `2 * wait_timeout` total). |

**Validation**:
- `state` enforced via `choices`.
- `instance_ids` non-empty; each entry matches `^i-[0-9a-f]{8,17}$` (cheap sanity check; AWS rejects anything weirder).
- `wait_timeout > 0`.

**Auth**: AWS credentials resolved via the standard boto3 credential chain. In practice this means the `AWS_PROFILE` env var, which commcare-cloud already exports via `aws_sign_in()` before launching ansible (see `src/commcare_cloud/commands/terraform/terraform.py:98` and the secrets backend at `src/commcare_cloud/environment/secrets/backends/aws_secrets/main.py:42-57`). No credential or profile parameters on the module — this matches the existing repo convention (no Ansible code currently passes a profile name as a module parameter).

**Check mode** (`supports_check_mode=True`):
- For `described`: always runs (read-only).
- For mutating states: fetch current state, compute what *would* change, return `changed` accordingly without calling the mutating API.

## Behavior per state

All mutating states first call `DescribeInstances` to read current state, then act only on instances that need changing (idempotency).

### `described` (read-only)
- Calls `DescribeInstances(InstanceIds=instance_ids)`.
- Returns `changed: false` and `instances: [...]` (see Return shape below).

### `started`
- Targets: instances currently in `stopped` or `stopping`.
  - Instances in `pending`/`running` are no-ops.
  - Instances in `terminated`/`shutting-down` cause module failure — can't start them.
- If `stopping` is present and `wait=true`, first wait for `stopped` (otherwise `StartInstances` would error).
- If no targets need change → `changed: false`, return current state.
- Else: `StartInstances(InstanceIds=targets)`. If `wait=true`, use boto3 `instance_running` waiter with `wait_timeout` budget.

### `stopped`
- Targets: instances currently in `running` or `pending`.
- If `pending` is present and `wait=true`, first wait for `running` (normalizes the contract — `StopInstances` on a `pending` instance technically works but ordering is cleaner this way).
- If no targets → `changed: false`.
- Else: `StopInstances(InstanceIds=targets)`. If `wait=true`, use `instance_stopped` waiter.
- Instances already in `stopping` (mid-transition initiated by someone else): if `wait=true`, wait for them to reach `stopped`. Reported as `changed: false` — `changed` reflects whether *this run* mutated AWS state.

### `restarted` (= stop, then start)
- Internally: run the `stopped` flow, then run the `started` flow.
- The stop phase is forced to `wait=true` regardless of the user's `wait` param — required for correctness, since `StartInstances` on a still-stopping instance fails. If user passed `wait=false`, emit `module.warn()` indicating the override.
- Start phase respects the user's `wait` param.
- `wait_timeout` applies to each phase independently.
- `changed: true` if either phase made any state change.
- **Mixed-state batch semantics**: if some instances are already `stopped`, the stop phase no-ops for them; the start phase then starts them. End state of all instances is `running`. This matches the intuitive contract: "after `restarted`, every instance is up."

### Failure modes
Module fails immediately if:
- Any instance ID does not exist (`InvalidInstanceID.NotFound`) — applies to all states including `described`.
- Any instance is `terminated` or `shutting-down` and the requested state is mutating (`started`, `stopped`, `restarted`). For `described`, terminated instances are reported as-is, not a failure.
- AWS API call returns a non-2xx response.
- Waiter exceeds `wait_timeout`.
- `boto3` not installed.

## Return value shape

```python
{
    "changed": bool,
    "state": str,                      # the requested state, echoed back
    "instances": [
        {
            "instance_id": "i-0abc...",
            "previous_state": "running",   # state before this module ran
            "current_state": "stopped",    # state after (post-wait if wait=true)
            "instance_type": "t3.medium",
            "availability_zone": "us-east-1a",
            "private_ip": "10.201.10.31",
            "public_ip": "34.x.x.x",       # null if none
            "tags": {"Name": "...", ...},
            "launch_time": "2026-04-13T12:34:56Z",
        },
        ...
    ],
    "skipped_instance_ids": ["i-0xxx..."],   # IDs that needed no action
    "diff": {
        "before": {"states": {"i-0abc...": "running", ...}},
        "after":  {"states": {"i-0abc...": "stopped", ...}},
    },
}
```

**Notes**:
- `instances` list order matches input `instance_ids` order.
- For `wait: false`, `current_state` reflects the state immediately after the API call returns (likely `pending`/`stopping`), not the eventual state.
- For `restarted`, `previous_state` = state before stop, `current_state` = state after start.

## Example playbook usage

```yaml
# Restart a single host, resolving its instance ID from inventory hostvars.
# region is omitted — picked up from AWS_REGION env var that commcare-cloud
# already exports when launching ansible.
- name: Restart proxy6-staging
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Reboot proxy6
      ec2_instance_state:
        instance_ids:
          - "{{ hostvars['10.201.11.133'].ec2_instance_id }}"
        state: restarted

# Stop all webworkers in batch
- name: Stop all webworkers
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Stop webworkers
      ec2_instance_state:
        instance_ids: >-
          {{ groups['webworkers']
             | map('extract', hostvars, 'ec2_instance_id')
             | list }}
        state: stopped

# Region override (rare — only if you need to target a non-default region)
- name: Describe an instance in another region
  hosts: localhost
  gather_facts: false
  tasks:
    - ec2_instance_state:
        instance_ids: ["i-0abc123def456"]
        state: described
        region: us-west-2
```

## Testing strategy

### Unit tests
- **File**: `tests/test_ec2_instance_state.py`
- **Tooling**: `unittest.mock` (stdlib, already used throughout `tests/`). No new dependencies.
- **Approach**: Build a small `FakeEC2Client` helper that returns canned `describe_instances` payloads and records `start_instances`/`stop_instances` calls. Waiters are mocked to return immediately. We are testing *our* control flow, not boto3.

### Cases
1. `described` returns expected shape.
2. `started` on already-running → `changed: false`, no `StartInstances` call recorded.
3. `started` on stopped → `changed: true`, `StartInstances` called with correct IDs, waiter invoked.
4. `stopped` on running → `changed: true` (symmetric to #3).
5. `restarted` on running → `StopInstances` then `StartInstances` in order; waiter called between.
6. Mixed batch (3 IDs, one already in target state) → only the other two are passed to the mutating call; return reports skipped ID.
7. Invalid instance ID (mock raises `ClientError("InvalidInstanceID.NotFound")`) → module fails with clean message.
8. `terminated` instance + `started` → module fails before API call.
9. Check mode: `started` on stopped instance → `changed: true`, no mutating API call.
10. `wait: false` → waiter not invoked; transitional state returned.
11. Empty `instance_ids` → validation error.
12. `restarted` with `wait: false` → `module.warn()` emitted; stop phase still waits.

### No integration tests against real AWS
Out of scope. Moto-style replay isn't justified for a single module. Real-world validation happens via the example playbook in a non-prod environment.

## Open follow-ups (out of scope for this design)

- A wrapper command (`commcare-cloud <env> ec2-restart <hostname>`) that invokes this module via an ad-hoc playbook. Useful but separable.
- Multi-region batch support. Would require either looping in the playbook or accepting a `region_map`. Defer until there's a concrete need.
