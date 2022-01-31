Hosting CommCare: Training Plan
===============================

Maintaining a stable and up-to-date CommCare HQ environment requires a
high level of technical skills.

Prerequisite knowledge
----------------------

Virtualization Stack
^^^^^^^^^^^^^^^^^^^^

Dimagi recommends that projects use a cloud hosting provider like Amazon
Web Services, Microsoft Azure, Google Cloud Platform, etc. For some
projects that is not possible, and those projects host on-premises using
VMWare, Citrix XenServer, OpenStack or just libvirt, etc.

If the team who will be managing the CommCare environment are also
responsible for managing the virtual infrastructure, it is important to
be familiar with the virtualization technology stack.

Online learning resources are available. Cloud hosting providers and
technology providers  also offer courses.


Linux
^^^^^

CommCare HQ is deployed on the Ubuntu distribution of the GNU/Linux
operating system. Familiarity with GNU/Linux is an important foundation
for hosting CommCare HQ. An excellent way to certify that staff have
that foundation is the LPIC-1 (the
`Linux Professional Institute <https://www.lpi.org/>`_ Certification
Level 1).

Course material is available in multiple languages. A lot of course
material is free of charge at https://learning.lpi.org/. In-person
training, online training, and exams are offered by affiliated
organizations in many countries.


Course plan
-----------

The following plan lays out the topics that you need to know as a
CommCare HQ DevOps engineer.

+---------------------------------------------------------+---------+
| A high-level understanding of the services that make up | 1 hour  |
| CommCare HQ. See the `CommCare HQ Services Overview`_.  |         |
|                                                         |         |
+---------------------------------------------------------+---------+
| A detailed understanding of the installation process:   | 1 hour  |
| See `Setting up a new CommCare HQ environment`_.        |         |
|                                                         |         |
+---------------------------------------------------------+---------+
| `Server management basics`_                             | 15 mins |
|                                                         |         |
+---------------------------------------------------------+---------+
| You should make sure you have reviewed the              | 1 hour  |
| documentation on `Firefighting`_, so that you are       |         |
| aware, in advance, of what can go wrong, and how to     |         |
| deal with situations before they occur.                 |         |
|                                                         |         |
+---------------------------------------------------------+---------+
| How to `backup and restore`_ persistent storage.        | 1 hour  |
|                                                         |         |
+---------------------------------------------------------+---------+
| Monitoring your infrastructure and services             | 15 mins |
| `using Datadog`_.                                       |         |
|                                                         |         |
+---------------------------------------------------------+---------+
| You should familiarize yourself with the                | 15 mins |
| `CommCare Forum`_. This is where                        |         |
| `announcements to the community`_ are made, and the     |         |
| best source of support.                                 |         |
|                                                         |         |
+---------------------------------------------------------+---------+


.. _CommCare HQ Services Overview: https://docs.google.com/presentation/d/1wR13WMgVXpT_tzXJLSgIL8l3sxELfAyQeAikX7IT39Q/edit#slide=id.p
.. _Setting up a new CommCare HQ environment: https://dimagi.github.io/commcare-cloud/setup/new_environment.html
.. _Server management basics: https://dimagi.github.io/commcare-cloud/commcare-cloud/basics
.. _Firefighting: https://dimagi.github.io/commcare-cloud/firefighting/
.. _backup and restore: https://dimagi.github.io/commcare-cloud/commcare-cloud/backup.html
.. _using Datadog: https://dimagi.github.io/commcare-cloud/monitoring/setup_datadog.html
.. _CommCare Forum: https://forum.dimagi.com/
.. _announcements to the community: https://forum.dimagi.com/c/platform-announce/8


..
    TODO: Convert all linked docs to ReStructuredText, so that we can
    use references instead of links. This gives us the flexibility to
    move sections around without breaking links.
