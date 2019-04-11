import fnmatch
import os

from jinja2 import Environment as JEnvironment
from parameterized import parameterized

from commcare_cloud.manage_commcare_cloud.datadog_monitors import get_datadog_jinja_environment


def get_jinja_templates():
    templates = []
    for root, dirnames, filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, '*.j2'):
            templates.append(os.path.join(root, filename))
    return templates


@parameterized(get_jinja_templates())
def test_jinja_templates(path):
    jinja_env = JEnvironment()
    datadog_jinja_env = get_datadog_jinja_environment()
    with open(path) as template:
        if 'manage_commcare_cloud/monitors' in path:
            datadog_jinja_env.parse(template.read(), filename=path)
        else:
            jinja_env.parse(template.read(), filename=path)
