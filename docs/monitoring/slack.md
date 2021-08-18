# Slack for notifications

commcare-cloud can be configured to send event notifications to Slack such as
pre and post deploy messages.

To configure commcare-cloud to send messages to Slack:

1. Create a [Slack app](https://api.slack.com/authentication/basics) and copy the
access token.
2. Set the access token as a commcare-cloud secret:

    Run the following command and paste in the token when prompted:
    ```shell
    commcare-cloud <env> secrets edit slack_token
    ```
3. Set the value of `slack_notifications_channel` in the environment `meta.yml` file. This
should be the name of the Slack channel to send notifications to.

    ```yml
    slack_notifications_channel: "deploy_notifications"
    ```
