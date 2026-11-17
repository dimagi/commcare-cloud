import os

import pytest

from commcare_cloud.environment.paths import ANSIBLE_DIR

LIBRARY_DIR = os.path.join(ANSIBLE_DIR, "library")


def library_modules():
    return sorted(
        name for name in os.listdir(LIBRARY_DIR)
        if os.path.isfile(os.path.join(LIBRARY_DIR, name))
    )


@pytest.mark.parametrize("name", library_modules())
def test_module_shebang_uses_ansible_python_interpreter(name):
    # Ansible replaces only a `#!/usr/bin/python` shebang with the host's
    # ansible_python_interpreter. ansible-core 2.17 quotes any other
    # interpreter as a single word, so `#!/usr/bin/env python3` fails with
    # "/usr/bin/env python3: not found".
    with open(os.path.join(LIBRARY_DIR, name)) as fh:
        shebang = fh.readline().rstrip("\n")
    assert shebang == "#!/usr/bin/python"
