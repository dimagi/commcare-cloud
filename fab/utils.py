import datetime
import os
import yaml

from fabric.api import execute, env

from const import PROJECT_ROOT


def execute_with_timing(fn, *args, **kwargs):
    start_time = datetime.datetime.utcnow()
    execute(fn, *args, **kwargs)
    if env.timing_log:
        with open(env.timing_log, 'a') as timing_log:
            duration = datetime.datetime.utcnow() - start_time
            timing_log.write('{}: {}\n'.format(fn.__name__, duration.seconds))


def get_pillow_env_config(environment):
    pillow_conf = {}
    pillow_file = os.path.join(PROJECT_ROOT, 'pillows', '{}.yml'.format(environment))
    if os.path.exists(pillow_file):
        with open(pillow_file, 'r+') as f:
            yml = yaml.load(f)
            pillow_conf.update(yml)
    else:
        return None

    return pillow_conf
