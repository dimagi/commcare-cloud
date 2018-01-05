import os
import yaml
from .paths import ENVIRONMENTAL_DEFAULTS_DIR, get_public_vars_filepath, ENVIRONMENTS_DIR


def get_consolidated_vars(environment):
    with open(os.path.join(ENVIRONMENTAL_DEFAULTS_DIR, 'public.yml')) as f:
        default_vars = yaml.load(f)
    with open(get_public_vars_filepath(environment)) as f:
        custom_vars = yaml.load(f)

    consolidated_vars = {}
    if default_vars:
        deep_update(consolidated_vars, default_vars)
    deep_update(consolidated_vars, custom_vars)
    return consolidated_vars


def deep_update(base, extra):
    for key, new_value in extra.items():
        if isinstance(new_value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], new_value)
        else:
            base[key] = new_value


def get_public_vars(environment):
    filename = get_public_vars_filepath(environment)
    with open(filename) as f:
        return yaml.load(f)


def get_expected_public_vars(environment):
    filename = os.path.join(ENVIRONMENTS_DIR, environment, 'expected-public.yml')
    with open(filename) as f:
        return yaml.load(f)
