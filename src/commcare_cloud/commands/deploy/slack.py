from enum import Enum
from datetime import datetime

import random
import requests
import re
from clint.textui import puts
from requests import RequestException

from commcare_cloud.colors import color_warning


class Emoji(Enum):
    success = 'checkered_flag'
    failure = 'x'
    success_reaction = 'white_check_mark'
    failure_reaction = 'x'

    slow_reaction = random.choice(['snail', 'turtle', 'tortoise_wag'])
    medium_reaction = random.choice(['meh', 'meh_blue', 'cat-roomba'])
    fast_reaction = random.choice(['racing_car', 'zap', 'dash', 'rocket', 'cat-roomba-exceptionally-fast'])

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
        action = "resumed" if context.resume else "started"
        message = f"Deploy of '{context.service_name}' to '{self.environment.meta_config.deploy_env}' {action}"
        blocks = self._get_message_blocks("*Deploy Started*", context)
        response = self._post_message(message, blocks)
        context.set_meta_value('slack_thread_ts', response["ts"])
        if self.environment.fab_settings_config.generate_deploy_diffs:
            diff_text = context.diff.get_slack_diff()
            for chunked_diff_text in self._chunk_diff(diff_text):
                diff_blocks = [{
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": chunked_diff_text}
                }]
                self._post_message("Deploy diff", diff_blocks, thread_ts=response["ts"])

    def _chunk_diff(self, diff_text, chunk_size=2800):
        # Slack has a limit of 3000 characters per message block
        # https://api.slack.com/reference/block-kit/blocks#section_fields
        diff_lines = diff_text.split('\n')
        current_chunk = []
        current_length = 0
        for line in diff_lines:
            line_length = len(line) + 1
            if current_length + line_length > chunk_size:
                yield '\n'.join(current_chunk)
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length
        if current_chunk:
            yield '\n'.join(current_chunk)

    def send_deploy_end_message(self, context, is_success):
        thread_ts = context.get_meta_value('slack_thread_ts')
        reaction_emoji = Emoji.success_reaction if is_success else Emoji.failure_reaction
        self._post_reaction(thread_ts, reaction_emoji)

        end = datetime.utcnow()
        duration = end - context.start_time

        if is_success:
            if duration.seconds < 60 * 15:
                speed_emoji = Emoji.fast_reaction
            elif duration.seconds > 60 * 30:
                speed_emoji = Emoji.slow_reaction
            else:
                speed_emoji = Emoji.medium_reaction
            self._post_reaction(thread_ts, speed_emoji)

        status = "completed" if is_success else "failed"
        duration = re.sub(r'\.\d+', '', str(duration))
        message = f"Deploy {status} in {duration}"
        self._post_message(message, self._get_text_blocks(message), thread_ts)

    def _post_message(self, notification_text, blocks, thread_ts=None):
        data = {
            "channel": self.channel,
            "text": notification_text,
            "blocks": blocks
        }
        if thread_ts:
            data["thread_ts"] = thread_ts
        response = self._post("https://slack.com/api/chat.postMessage", data)
        return response.json()

    def _get_message_blocks(self, message, context):
        env_name = self.environment.meta_config.deploy_env
        return self._get_text_blocks(message) + [
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

    def _get_text_blocks(self, message):
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            }
        }]

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
