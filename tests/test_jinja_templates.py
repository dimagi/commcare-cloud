import fnmatch
import os

from jinja2 import Environment as JEnvironment


def test_jinja_templates():
    templates = []
    for root, dirnames, filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, '*.j2'):
            templates.append(os.path.join(root, filename))

    jinja_env = JEnvironment()
    for path in templates:
        with open(path) as template:
            jinja_env.parse(template.read(), filename=path)
