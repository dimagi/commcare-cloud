import fnmatch
import os

from jinja2 import Environment as JEnvironment
from parameterized import parameterized


def get_jinja_templates():
    templates = []
    for root, dirnames, filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, '*.j2'):
            templates.append(os.path.join(root, filename))
    return templates


@parameterized(get_jinja_templates())
def test_jinja_templates(path):
    jinja_env = JEnvironment()
    with open(path) as template:
        jinja_env.parse(template.read(), filename=path)
