import json
import os.path
from pathlib import Path
from unittest.mock import patch

from commcare_cloud import ansible as cloud_ansible


def run(module, args):
    """Run ansible module

    Callers are responsible for cleanup of changed system state.
    Arguments (paths, etc.) should reference temporary resources that
    can later be cleaned up by the caller. For example, utilities like
    ``testil.tempdir()`` can be used to create temporary directories in
    which the module can safely work without affecting other parts of
    the system on which the test is running.

    Modules that require elevated privileges are likely to be difficult
    to test, and may require mocking or other techniques to ensure the
    host system is not changed in an unsafe way when the module is run.

    When the ``module`` parameter is a string it will be loaded from
    src/commcare_cloud/ansible/library (an absolute file path may be
    provided to load from some other location); otherwise a module
    object is expected.
    """
    def exit_json(*args, **kw):
        raise Exit(kw)
    def fail_json(*args, **kw):
        raise Fail(kw.get("msg", repr(kw)), kw)
    if isinstance(module, (str, Path)):
        module = import_module(module)
    with _module_args_patch(args), patch.multiple(
        module.AnsibleModule,
        fail_json=fail_json,
        exit_json=exit_json,
    ):
        try:
            module.main()
        except Exit as result:
            return result.args[0]
        raise AssertionError("module did not call exit_json or fail_json")


def import_module(module_path):
    from importlib.machinery import SourceFileLoader
    from importlib.util import spec_from_loader, module_from_spec
    if isinstance(module_path, str) and os.path.sep not in module_path:
        library_path = Path(cloud_ansible.__file__).with_name("library")
        module_path = library_path / module_path
        if not module_path.exists() and not module_path.name.endswith(".py"):
            module_path = library_path / (module_path.name + ".py")
    module_path = str(module_path)
    try:
        return _module_cache[module_path]
    except KeyError:
        pass
    module_name = module_path.replace("/", ".")
    loader = SourceFileLoader(module_name, module_path)
    spec = spec_from_loader(module_name, loader)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    _module_cache[module_path] = mod
    return mod


_module_cache = {}


def _module_args_patch(args):
    # https://github.com/ansible/ansible/blob/devel/test/units/modules/utils.py
    from ansible.module_utils import basic
    from ansible.module_utils.common.text.converters import to_bytes
    if '_ansible_remote_tmp' not in args:
        args['_ansible_remote_tmp'] = '/tmp'
    if '_ansible_keep_remote_files' not in args:
        args['_ansible_keep_remote_files'] = False
    data = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': args}))
    return patch.object(basic, "_ANSIBLE_ARGS", data)


class Exit(SystemExit):
    pass


class Fail(SystemExit):
    pass
