import difflib

import yaml


def yaml_diff(obj_1, obj_2):
    yaml_lines_1 = yaml.safe_dump(obj_1, width=1000).splitlines()
    yaml_lines_2 = yaml.safe_dump(obj_2, width=1000).splitlines()
    return '\n'.join(list(difflib.ndiff(yaml_lines_1, yaml_lines_2)))
