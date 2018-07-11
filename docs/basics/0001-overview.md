## What is commcare-cloud?

`commcare-cloud` is a python-based command line tool that uses
the open source technologies Ansible and Fabric to automate everything
you need in order to run a production CommCare cluster.

While it is possible to install on a laptop with a linux-like command line interface,
it is primarily designed to be run on the machine that is hosting CommCare.
(If you are hosting CommCare on more than one machine,
`commcare-cloud` only needs to be installed on one of them.)
In this documentation, we will call the machine on which `commcare-cloud` is installed
the "control machine". If you are hosting CommCare on a single machine,
that machine is also the control machine.

---

Overview | [Installation ➡︎︎](0002-installation.md)
