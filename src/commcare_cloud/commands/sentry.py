from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import json
import sys

import requests

from commcare_cloud.environment.main import get_environment
from .command_base import CommandBase, Argument


class ExportSentryEvents(CommandBase):
    command = 'export-sentry-events'
    help = (
        "Export Sentry events. One line per event JSON."
    )

    arguments = (
        Argument('-k', '--api-key', help="Sentry API Key", required=True),
        Argument('-i', '--issue-id', help="Sentry project ID", required=True),
        Argument('--full', action='store_true', help="Export the full event details"),
        Argument('--cursor', help="Starting position for the cursor"),
    )

    def run(self, args, unknown_args):
        env = get_environment(args.env_name)

        url = "https://sentry.io/api/0/issues/{}/events/".format(args.issue_id)

        params = {'environment': env.meta_config.env_monitoring_id}
        if args.full:
            params['full'] = True
        if args.cursor:
            params['cursor'] = args.cursor

        while True:
            resp = requests.get(url, params, headers={
                'Authorization': 'Bearer {}'.format(args.api_key)
            })
            events = resp.json()
            last_date = None
            for event in events:
                last_date = event.get('dateCreated')
                print(json.dumps(event))

            # see https://docs.sentry.io/api/pagination/
            links = resp.headers['Link']
            prev, next = links.split(',')
            next_url, rel, results, cursor = next.split(';')
            if results.strip() != 'results="true"':
                return

            last_date = last_date or 'unknown'
            sys.stderr.write("Late event from {}. Fetching next page: {}\n".format(last_date, cursor.strip()))
            url = next_url.strip()[1:-1]
            if 'cursor' in params:
                del params['cursor']
