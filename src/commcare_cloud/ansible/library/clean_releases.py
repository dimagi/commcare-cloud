#! /usr/bin/env python3
from datetime import datetime
from pathlib import Path

from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type


DOCUMENTATION = """
---
module: clean_releases

short_description: Delete old releases.

description: Delete old releases, but retain the current release, files
    that are not directories, directories in the "exclude" list, any
    releases that contain a "KEEP_UNTIL__%Y-%m-%d_%H.%M" file where the
    UTC date in the filename is in the future, as well as the most
    recent "keep" (default 2) releases, proiritizing those that contain
    a ".build-complete" file. Releases are sorted in reverse by name to
    determine recency. The "exclude" releases do not count toward the
    "keep" releases, however the "current" release does count if it is
    not explicitly excluded.

version_added: "1.0.0"

options:
    path:
        description: The releases directory path.
        required: true
        type: str
    shared_dir_for_staticfiles:
        description: Shared directory containing staticfiles caches.
        required: false
        type: str
    keep:
        description: The number of releases to keep. Default: 2
        required: false
        default: 2
        type: int
    exclude:
        description: List of directory names to exclude from cleanup.
        required: false
        default: []
        type: list
        elements: str

extends_documentation_fragment:
    - commcare_cloud.ansible

author:
    - Daniel Miller (@millerdev)
"""

EXAMPLES = """
- name: Clean releases
  clean_releases:
    path: "/path/to/releases"
    exclude:
      - 2023-03-07_13.16
"""

RETURN = """
changed:
    description: Changed flag. True if any releases were removed.
    type: bool
diff:
    description: Dict of releases before and after states.
    type: dict
    sample: {'before': {'releases': [...]}, 'after': {'releases': [...]}}
"""


def main():
    module_args = {
        'path': {'type': 'str', 'required': True},
        'keep': {'type': 'int', 'default': 2},
        'shared_dir_for_staticfiles': {'type': 'str'},
        'exclude': {'type': 'list', 'default': [], 'elements': 'str'},
    }
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )
    params = module.params
    releases_path = Path(params["path"])
    _shared_dir = params["shared_dir_for_staticfiles"]
    shared_dir = Path(_shared_dir) if _shared_dir else None
    keep = params["keep"]
    current_release = (releases_path / "current").resolve()
    exclude = set(params["exclude"]) | {"current"}
    if current_release.exists() and current_release.name not in exclude:
        exclude.add(current_release.name)
        keep -= 1

    before = {p.name for p in releases_path.iterdir() if p.is_dir() and not p.name.startswith('.')}
    before_list = sorted(before)
    diff = {'before': {'releases': before_list}, 'after': {'releases': before_list}}
    result = {'changed': False, 'diff': diff}
    exclude.update(name for name in before if should_keep(releases_path / name))

    def prioritize(name):
        build_complete = releases_path / name / BUILD_COMPLETE
        return (int(build_complete.exists()), name)

    to_remove = sorted(before - exclude, key=prioritize, reverse=True)[keep:]
    assert current_release.name not in to_remove, (to_remove, current_release)
    if to_remove:
        result["changed"] = True
        diff["after"]['releases'] = after = sorted(before - set(to_remove))
        assert len(after) >= params["keep"], (diff, params["keep"])
        if not module.check_mode:
            keep_shares = {get_code_version(releases_path / k) for k in before - set(to_remove)}
            keep_shares.add(None)  # None prevents rm when get_code_version(...) returns None
            for name in to_remove:
                if shared_dir:
                    delete_shared(releases_path / name, shared_dir, keep_shares, module)
                module.run_command(["rm", "-rf", releases_path / name])

    module.exit_json(**result)


def should_keep(release_path):
    for keep_path in release_path.glob(KEEP_UNTIL_PREFIX + "*"):
        until = get_until_date(keep_path.name)
        if until and until > datetime.utcnow():
            return True
    return False


def get_until_date(filename):
    until = filename[len(KEEP_UNTIL_PREFIX):]
    try:
        return datetime.strptime(until, DATE_FMT)
    except Exception:
        return None


def delete_shared(release_path, shared_dir, keep_shares, module):
    # It's possible for multiple processes on different hosts to
    # execute this concurrently, which could cause errors like
    #
    #   rm: cannot remove file ... : No such file or directory
    #
    # To avoid that, the parent directory is renamed (an atomic
    # operation that will only succeed on one host) before it is
    # removed.
    code_version = get_code_version(release_path)
    if code_version not in keep_shares and (shared_dir / code_version).exists():
        path = shared_dir / code_version
        path_to_remove = path.with_suffix(".obsolete")
        rc = module.run_command(["mv", path, path_to_remove])[0]
        if rc == 0:
            module.run_command(["rm", "-rf", path_to_remove])


def get_code_version(release_path):
    if not (release_path / STATICFILES_VERSION).exists():
        return None
    with open(release_path / STATICFILES_VERSION) as fh:
        return fh.read().rstrip() or None


BUILD_COMPLETE = '.build-complete'
STATICFILES_VERSION = '.staticfiles-version'
KEEP_UNTIL_PREFIX = 'KEEP_UNTIL__'
DATE_FMT = '%Y-%m-%d_%H.%M'


if __name__ == '__main__':
    main()
