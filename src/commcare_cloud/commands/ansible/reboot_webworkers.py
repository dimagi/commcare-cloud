# coding=utf-8
import os
import shlex
import subprocess
import tempfile
import time
from copy import deepcopy
from datetime import datetime, timezone

from clint.textui import puts

from commcare_cloud.alias import commcare_cloud
from commcare_cloud.cli_utils import check_branch, print_command
from commcare_cloud.colors import (
    color_error,
    color_notice,
    color_summary,
    color_warning,
)
from commcare_cloud.commands import shared_args
from commcare_cloud.commands.ansible.helpers import (
    DEPRECATED_ANSIBLE_ARGS,
    AnsibleContext,
    get_common_ssh_args,
    get_user_arg,
)
from commcare_cloud.commands.command_base import Argument, CommandBase
from commcare_cloud.environment.paths import ANSIBLE_DIR
from commcare_cloud.parse_help import (
    ANSIBLE_HELP_OPTIONS_PREFIX,
    add_to_help_text,
    filtered_help_message,
)
from commcare_cloud.user_utils import get_dev_username


class RebootWebworkers(CommandBase):
    command = 'reboot-webworkers'
    aliases = ('rw',)
    help = """
    Reboot all webworkers with Slack notifications and logging.

    This command will:
    - Send a Slack notification when starting the reboot process
    - Log all output to a file
    - Send the log file to Slack in the specified channel
    - Add a success (✅) or failure (❌) emoji based on the result

    Example:
    ```
    commcare-cloud <env> reboot-webworkers --slack-channel=alerts-production
    ```
    """
    arguments = (
        shared_args.SKIP_CHECK_ARG,
        shared_args.QUIET_ARG,
        shared_args.BRANCH_ARG,
        shared_args.STDOUT_CALLBACK_ARG,
        shared_args.FACTORY_AUTH_ARG,
        shared_args.LIMIT_ARG,
        Argument('--slack-channel', help="""
            Slack channel to send notifications to (e.g., alerts-production, hq-ops).
            If not specified, will use the environment's default slack_notifications_channel.
        """),
        Argument('--service-name', default='webworkers', help="""
            Name of the service being rebooted (default: webworkers).
            This will be used in Slack notifications.
        """),
    )

    def modify_parser(self):
        add_to_help_text(self.parser, "\n{}\n{}".format(
            "The ansible-playbook options below are available as well:",
            filtered_help_message(
                "ansible-playbook -h",
                below_line=ANSIBLE_HELP_OPTIONS_PREFIX,
                above_line=None,
                exclude_args=DEPRECATED_ANSIBLE_ARGS + [
                    '--help',
                    '--diff',
                    '--check',
                    '-i',
                    '--ask-vault-pass',
                    '--vault-password-file',
                    '--limit',
                ],
            )
        ))

    def run(self, args, unknown_args):
        ansible_context = AnsibleContext(args)
        check_branch(args)
        use_factory_auth = getattr(args, 'use_factory_auth', False)
        
        log_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False)
        log_file_path = log_file.name
        log_file.close()
        
        try:
            return self._run_reboot_with_notifications(
                args, ansible_context, log_file_path, use_factory_auth, unknown_args
            )
        except Exception as e:
            puts(color_error(f"Error running reboot playbook: {e}"))
            return 1
        finally:
            try:
                os.unlink(log_file_path)
            except OSError:
                pass

    def _run_reboot_with_notifications(self, args, ansible_context, log_file_path, use_factory_auth, unknown_args):
        environment = ansible_context.environment
        service_name = args.service_name
        slack_channel = "restart-tests" # args.slack_channel or environment.meta_config.slack_notifications_channel
        
        if not slack_channel:
            puts(color_error("No Slack channel specified and no default channel configured in environment"))
            return 1

        slack_client = None
        try:
            from commcare_cloud.commands.deploy.slack import SlackClient

            # Create a temporary environment with the specified channel
            temp_env = environment
            if args.slack_channel:
                # Create a copy of the environment with the specified channel
                temp_env = deepcopy(environment)
                temp_env.meta_config.slack_notifications_channel = args.slack_channel
            slack_client = SlackClient(temp_env)
        except Exception as e:
            puts(color_warning(f"Failed to initialize Slack client: {e}"))
            slack_client = None

        start_time = datetime.now(timezone.utc)
        thread_ts = None
        if slack_client:
            thread_ts = self._send_slack_start_notification(slack_client, environment, service_name)

        puts(color_summary(f"[{self.command}] Starting reboot of {service_name}..."))
        puts(color_summary(f"[{self.command}] Logging output to: {log_file_path}"))
        
        success = False
        try:
            result = self._run_ansible_playbook_with_logging(
                'reboot_all_webworkers.yml', ansible_context, args.skip_check, 
                args.quiet, args.limit, use_factory_auth, unknown_args, log_file_path
            )
            success = result == 0
        except Exception as e:
            puts(color_error(f"Error running reboot playbook: {e}"))
            success = False

        if slack_client and thread_ts:
            try:
                self._send_log_file_to_slack(slack_client, log_file_path, thread_ts, service_name)
                puts(color_summary(f"[{self.command}] Log file uploaded to Slack"))
            except Exception as e:
                puts(color_warning(f"Failed to send log file to Slack : {e}"))
                puts(color_notice(f"[{self.command}] Log file is available at: {log_file_path}"))

        if slack_client and thread_ts:
            self._send_slack_completion_notification(slack_client, thread_ts, start_time, success, service_name)

        if success:
            puts(color_summary(f"[{self.command}] Reboot of {service_name} completed successfully"))
        else:
            puts(color_error(f"[{self.command}] Reboot of {service_name} failed"))
            
        return 0 if success else 1

    def _run_ansible_playbook_with_logging(self, playbook, ansible_context, skip_check, quiet, limit, use_factory_auth, unknown_args, log_file_path):
        """Run ansible playbook with output logged to file"""

        def get_limit(environment):
            import re
            limit_parts = []
            if limit:
                limit_parts = re.split('[,:]', limit)
            if 'ansible_skip' in environment.sshable_hostnames_by_group:
                limit_parts.append('!ansible_skip')

            if limit_parts:
                return '--limit', ','.join(limit_parts)
            else:
                return ()

        environment = ansible_context.environment
        playbook_path = os.path.join(ANSIBLE_DIR, playbook)
        
        cmd_parts = list((
            'ansible-playbook',
            playbook_path,
            '-i', environment.paths.inventory_source,
            '-e', '@{}'.format(environment.paths.public_yml),
            '-e', '@{}'.format(environment.paths.generated_yml),
            '--diff',
        ) + get_limit(environment) + (unknown_args or ()))

        public_vars = environment.public_vars
        env_vars = ansible_context.build_env()
        cmd_parts.extend(get_user_arg(public_vars, unknown_args or [], use_factory_auth))
        cmd_parts.extend(environment.secrets_backend.get_extra_ansible_args())
        cmd_parts.extend(get_common_ssh_args(environment, use_factory_auth=use_factory_auth))
        
        cmd = ' '.join(shlex.quote(arg) for arg in cmd_parts)
        print_command(cmd)
        
        with open(log_file_path, 'w') as log_file:
            log_file.write(f"Reboot command started at: {datetime.now(timezone.utc)}\n")
            log_file.write(f"Command: {cmd}\n")
            log_file.write("-" * 80 + "\n")
            log_file.flush()
            
            try:
                with environment.generated_yml():
                    process = subprocess.Popen(
                        cmd_parts, 
                        env=env_vars,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    for line in process.stdout:
                        log_file.write(line)
                        log_file.flush()
                        # Also print to console
                        puts(line.rstrip())
                    
                    return_code = process.wait()
                    log_file.write(f"\nCommand completed with return code: {return_code}\n")
                    return return_code
                    
            except KeyboardInterrupt:
                log_file.write("\nCommand interrupted by user\n")
                return 1

    def _send_log_file_to_slack(self, slack_client, log_file_path, thread_ts, service_name):
        """Send the log file to Slack as a file upload"""
        import requests
        
        try:
            with open(log_file_path, 'rb') as log_file:
                files = {
                    'file': (f'reboot_{service_name}_{int(time.time())}.log', log_file, 'text/plain')
                }
                data = {
                    'channels': slack_client.channel,
                    'thread_ts': thread_ts,
                    'title': f'Reboot Log - {service_name}',
                    'initial_comment': f'Log file for {service_name} reboot operation'
                }
                
                headers = {'Authorization': f'Bearer {slack_client.slack_token}'}
                response = requests.post(
                    'https://slack.com/api/files.upload',
                    files=files,
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                if not result.get('ok'):
                    raise Exception(f"Slack API error: {result.get('error', 'Unknown error')}")
                    
        except Exception as e:
            raise Exception(f"Failed to upload log file to Slack: {e}")

    def _send_slack_start_notification(self, slack_client, environment, service_name):
        """Send start notification to Slack and return thread timestamp"""
        try:
            message = f"🔄 Initiating restart of {service_name} on {environment.meta_config.deploy_env}"
            blocks = [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                }
            }, {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment*: {environment.meta_config.deploy_env}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Service*: {service_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*User*: {get_dev_username(environment.name)}"
                    }
                ]
            }]
            response = slack_client._post_message(message, blocks)
            thread_ts = response.get("ts")
            puts(color_summary(f"[{self.command}] Slack notification sent to #{slack_client.channel}"))
            return thread_ts
        except Exception as e:
            puts(color_warning(f"Failed to send Slack start notification: {e}"))
            return None

    def _send_slack_completion_notification(self, slack_client, thread_ts, start_time, success, service_name):
        """Send completion notification to Slack with status emoji"""
        try:
            end_time = datetime.now(timezone.utc)
            duration = end_time - start_time
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            
            status = "completed successfully" if success else "failed"
            emoji = "✅" if success else "❌"
            message = f"{emoji} Reboot of {service_name} {status} in {duration_str}"
            
            slack_client._post_message(message, [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                }
            }], thread_ts)
            
            puts(color_summary(f"[{self.command}] Slack completion notification sent"))
        except Exception as e:
            puts(color_warning(f"Failed to send Slack completion notification: {e}"))
