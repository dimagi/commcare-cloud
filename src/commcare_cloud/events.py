import json

import requests
from fabric.colors import red


def publish_deploy_event(name, component, environment):
    url = environment.fab_settings_config.deploy_event_url
    if not url:
        return
    token = environment.get_secret("deploy_event_token")
    if not token:
        print(red(f"skipping {name} event: deploy_event_token secret not set"))
        return
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = json.dumps({
        "event_type": name,
        "client_payload": {
            "component": component,
            "environment": environment.meta_config.deploy_env,
        },
    })
    response = requests.post(url, data=data, headers=headers)
    if 200 <= response.status_code < 300:
        print(f"triggered {name} event")
    else:
        print(red(f"{name} event status: {response.status_code}"))
