# Expectations for Ongoing Maintenance

Like any software project, CommCareHQ requires active maintenance to be kept
up-to-date. As project maintainers, Dimagi frequently makes changes such as
library upgrades, bug fixes, feature development, database migrations, and
infrastructure improvements. Whenever possible, these changes are made to be
rolled out automatically with a regular deploy, but occasional larger changes
require direct handling to minimize disruptions.

To minimize friction, we recommend that anyone hosting an instance of CommCareHQ
commit to keeping their environment up to date by following the guidelines
described on this page. It can become much more challenging to update an
environment that has been neglected for an extended period.


## Monitor the developers forum

Subscribe to the [developers forum](https://forum.dimagi.com/c/developers/5) to
keep in contact with Dimagi and other parties hosting CommCare. Dimagi will
announce important changes there, such as upcoming upgrades.


## Deploy CommCareHQ at least once every two weeks

CommCareHQ is under continuous development, so to ensure you are running an
up-to-date version of the code, you should be deploy changes at least every two
weeks.

Some code changes are meant to be rolled out over the course of two or three
deploys, which allows us to minimize or eliminate the disruptions caused by
things like backwards-incompatible database changes. It is important for the
developers to be able to make assumptions about how these changes will impact
existing environments.


## Update commcare-cloud before every deploy and check the changelog

`commcare-cloud` is developed in conjunction with CommCareHQ. To be on the safe
side, it's best to update just before deploying CommCareHQ. When you do so,
check for new entries in the [changelog](https://dimagi.github.io/commcare-cloud/changelog/),
which should alert you of any new changes which might require you to take
action. We recommend you take a look through the current entries to get an idea
of what these changes might look like.

Take the action described in each new changelog entry within the compatibility
window, if applicable. Aside from urgent security issues, there should be a
window during which you can plan for downtime or for a more involved upgrade. If
you will be unable to apply the change in the window, please reach out on the
forum.

After the window expires, Dimagi will drop support for the old version. You may
then face additional difficulty in deploying the change, as well as
incompatibility problems on your server.
