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
        Argument('-k', '--api-key', help="Sentry API Key"),
        Argument('-q', '--query', help="Text query", default=None),
        Argument('--start', help="UTC start date. Format YYYY-MM-DDTHH:MM:SS", default=None),
        Argument('--end', help="UTC end date. Format YYYY-MM-DDTHH:MM:SS", default=None),
        Argument('--project-id',
                 help="Sentry project ID. If not supplied the value for the environment "
                      "will be used (requires Vault access)", default=None
         ),
        Argument('--organization', help="Organization slug", default='dimagi'),
    )

    def run(self, args, unknown_args):
        env = get_environment(args.env_name)

        url = "https://sentry.io/api/0/organizations/{organization_slug}/events/".format(
            organization_slug=args.organization_slug,
        )

        params = {'environment': env.meta_config.env_monitoring_id}
        if args.query:
            params['query'] = args.query
        if args.start:
            params['start'] = args.start
        if args.end:
            params['end'] = args.end
        if args.project_id:
            params['project'] = args.project_id
        else:
            params['project'] = env.get_vault_var('localsettings_private.SENTRY_PROJECT_ID')

        while True:
            resp = requests.get(url, params, headers={
                'Authorization': 'Bearer {}'.format(args.api_key)
            })
            events = resp.json()
            for event in events:
                print(json.dumps(event))

            # see https://docs.sentry.io/api/pagination/
            links = resp.headers['Link']
            prev, next = links.split(',')
            next_url, rel, results, cursor = next.split(';')
            if results.strip() != 'results="true"':
                return

            sys.stderr.write("Fetching next page: {}\n".format(cursor.strip()))
            url = next_url.strip()[1:-1]
