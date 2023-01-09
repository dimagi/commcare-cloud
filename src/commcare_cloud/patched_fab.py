
from commcare_cloud.cli_utils import log_command

@log_command
def main():
    patch_fabric_imports()
    import fabric.main
    return fabric.main.main()


def patch_fabric_imports():
    import collections
    from collections.abc import Mapping
    collections.Mapping = Mapping
