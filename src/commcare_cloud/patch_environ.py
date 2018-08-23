import os


def patch_environ():
    if 'ANSIBLE_CONFIG' not in os.environ:
        # this must happen before other imports so that it's present when `ansible.constants` is imported
        from commcare_cloud.environment.paths import ANSIBLE_DIR
        os.environ['ANSIBLE_CONFIG'] = os.path.join(ANSIBLE_DIR, 'ansible.cfg')
