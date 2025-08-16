Settings in ``public.yml``
==========================

The following are settings found in the ``public.yml`` file. Many are
passed on to CommCare HQ in its ``localsettings.py`` file:

Email addresses
---------------

daily_deploy_email:
    Notifications are emailed to this address when a deploy completes.

root_email:
    Used as the email address when requesting SSL certificates from
    LetsEncrypt. Proxy server notifications are also emailed to this
    address.

server_email:
    Used as the "from" or "reply to" address by CommCare HQ for:

    * Bug reports from CommCare users
    * Notifications of requests for project spaces or organizations
    * Notifications from the ``sync_prepare_couchdb_multi`` management
      command

server_admin_email:
    All CommCare HQ web service (Django) administrator email
    notifications are sent to this address. (It is used as the address
    for Django ADMINS and MANAGERS.)

default_from_email:
    Used as the "from" address for:

    * All emails sent via the Celery email queue
    * "Dimagi Finance" and "Dimagi Accounting" on automated accounting
      reports, sales requests, subscription reminders, invoices, and weekly
      digests of subscriptions
    * The ``send_email`` management command

return_path_email:
    The email account for receiving bounced emails. This needs to use
    an IMAP4+SSL compliant service. It is tested with GMail.

    Used by the ``process_bounced_emails`` management command.

support_email:
    This is the address given to users to reach out to for support in
    situations where they may have queries, for example, in password
    reset emails, project space transfers, the 404 page, among others.

    In non-Dimagi environments this address is given as the email for
    Support in CommCare apps.

accounts_email:
    The email account to which generated invoices and weekly digests
    are sent, and to which subscription reminders are CCed. It is also
    the contact address given for subscription changes.

data_email:
    The address to which the monthly Global Impact Report is sent.

subscription_change_email:
    Notifications of subscription changes are sent to this address.

internal_subscription_change_email:
    Notifications of internal changes to subscriptions are sent to this address.

billing_email:
    Enterprise Plan and Annual Plan requests are sent to this address.
    It is also given as the contact address for signing up for new
    subscriptions.

invoicing_contact_email:
    The contact email address given on invoices, and notifications
    regarding payment methods.

growth_email:
    Subscription downgrade and pause notifications are sent to and
    BCCed to this address.

saas_ops_email:
    Unused

saas_reporting_email:
    The "Credits On HQ" report is sent to this address for the
    "production" and "india" Dimagi environments.

master_list_email:
    This address is sent a list of self-started projects which have
    incomplete info and over 200 form submissions.

sales_email:
    Given as the contact address if users need more OData feeds, more
    Report Builder reports, or messaging/SMS features.

privacy_email:
    Given as a contact address in the End User License Agreement.

feedback_email:
    Feedback for features is sent to this address.

eula_change_email:
    When a user changes a custom End User License Agreement or
    data-sharing properties for their domain, a notification is sent to
    this address.

contact_email:
    Unused

soft_assert_email:
    Soft asserts in the source code that that are called with
    ``send_to_ops`` send to this email address.

new_domain_email:
    This address is notified when a user requests a project space or
    organization.
