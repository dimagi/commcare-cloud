from __future__ import absolute_import
import os

from jinja2 import Environment, FileSystemLoader


def render_template(name, context, template_root):
    env = Environment(loader=FileSystemLoader(template_root))
    return env.get_template(name).render(context)
