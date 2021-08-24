from enum import Enum

import requests
from clint.textui import puts
from requests import RequestException

from commcare_cloud.colors import color_warning


class Emoji(Enum):
    success = 'checkered_flag'
    failure = 'x'
    success_reaction = 'white_check_mark'
    failure_reaction = 'x'

    @property
    def code(self):
        return f":{self.value}:"


class SlackException(Exception):
    pass


def notify_slack_deploy_start(environment, context):
    try:
        client = SlackClient(environment)
    except SlackException:
        return

    try:
        client.send_deploy_start_message(context)
    except SlackException as e:
        puts(color_warning(f"Error sending Slack notification: {e}"))


def notify_slack_deploy_end(environment, context, is_success):
    try:
        client = SlackClient(environment)
    except SlackException:
        return

    try:
        client.send_deploy_end_message(context, is_success)
    except SlackException as e:
        puts(color_warning(f"Error sending Slack notification: {e}"))


class SlackClient:
    def __init__(self, environment):
        self.environment = environment
        try:
            self.slack_token = environment.get_secret("slack_token")
        except Exception as e:
            raise SlackException(e)
        self.channel = environment.meta_config.slack_notifications_channel
        if not self.channel:
            raise SlackException("Channel not configured")

        # bot must have joined the channel in order to create reactions
        self._post("https://slack.com/api/conversations.join", {"channel": self.channel})

    def send_deploy_start_message(self, context):
        blocks = self._get_message_blocks("*Deploy Started*", context)
        response = self._post_blocks(blocks)
        context.set_meta_value('slack_thread_ts', response["ts"])

    def send_deploy_end_message(self, context, is_success):
        thread_ts = context.get_meta_value('slack_thread_ts')
        if is_success:
            message = f"*Deploy Success* {Emoji.success.code}"
        else:
            message = f"*Deploy Failed* {Emoji.failure.code}"
        blocks = self._get_message_blocks(message, context)
        reaction_emoji = Emoji.success_reaction if is_success else Emoji.failure_reaction
        self._post_reaction(thread_ts, reaction_emoji)
        self._post_blocks(blocks, thread_ts=thread_ts)

    def _post_blocks(self, blocks, thread_ts=None):
        data = {
            "channel": self.channel,
            "blocks": blocks
        }
        if thread_ts:
            data["thread_ts"] = thread_ts
        response = self._post("https://slack.com/api/chat.postMessage", data)
        return response.json()

    def _get_message_blocks(self, message, context):
        env_name = self.environment.meta_config.deploy_env
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment*: {env_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Service*: {context.service_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*User*: {context.user}"
                    }
                ]
            }
        ]

    def _post_reaction(self, thread_ts, emoji):
        data = {
            "channel": self.channel,
            "name": emoji.value,
            "timestamp": thread_ts
        }
        self._post("https://slack.com/api/reactions.add", data)

    def _post(self, url, data):
        headers = {'Authorization': f'Bearer {self.slack_token}'}
        response = requests.post(url, json=data, headers=headers)
        try:
            response.raise_for_status()
        except RequestException as e:
            raise SlackException(e)
        return response
