# Slack for notifications

commcare-cloud can be configured to send event notifications to Slack such as
pre and post deploy messages.

To configure commcare-cloud to send messages to Slack:

1. Create a [Slack app](https://api.slack.com/authentication/basics) and copy the
access token.

   The app  will require the following authentication scopes:

   1. channels:join
   2. chat:write
   3. reactions:write

2. Set the access token as a commcare-cloud secret:

    Run the following command and paste in the token when prompted:
    ```shell
    commcare-cloud <env> secrets edit slack_token
    ```
3. Set the value of `slack_notifications_channel` in the environment `meta.yml` file. This
should be the ID of the Slack channel to send notifications to.

    ```yml
    slack_notifications_channel: "C0WLJ3XYZ"
    ```

   To get the ID you can open the channel in a web browser and copy the ID from the URL:

   ```
   https://app.slack.com/client/.../C0WLJ3XYZ
   ```
