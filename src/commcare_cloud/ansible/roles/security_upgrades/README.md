# Ansible weareinteractive.apt role

[![Build Status](https://img.shields.io/travis/weareinteractive/ansible-apt.svg)](https://travis-ci.org/weareinteractive/ansible-apt)
[![Galaxy](http://img.shields.io/badge/galaxy-weareinteractive.apt-blue.svg)](https://galaxy.ansible.com/weareinteractive/apt)
[![GitHub Tags](https://img.shields.io/github/tag/weareinteractive/ansible-apt.svg)](https://github.com/weareinteractive/ansible-apt)
[![GitHub Stars](https://img.shields.io/github/stars/weareinteractive/ansible-apt.svg)](https://github.com/weareinteractive/ansible-apt)

> `weareinteractive.apt` is an [Ansible](http://www.ansible.com) role which:
>
> * updates apt
> * cleans up apt
> * configures apt
> * installs packages
> * add repositories
> * add keys
> * manages unattended upgrades
> * optionally alters solution cost
> * optionally allows filesystems to be remounted

**Note:**

> Since Ansible Galaxy supports [organization](https://www.ansible.com/blog/ansible-galaxy-2-release) now, this role has moved from `franklinkim.apt` to `weareinteractive.apt`!

## Installation

Using `ansible-galaxy`:

```shell
$ ansible-galaxy install weareinteractive.apt
```

Using `requirements.yml`:

```yaml
- src: weareinteractive.apt
```

Using `git`:

```shell
$ git clone https://github.com/weareinteractive/ansible-apt.git weareinteractive.apt
```

## Dependencies

* Ansible >= 2.4

## Variables

Here is a list of all the default variables for this role, which are also available in `defaults/main.yml`.

```yaml
---
# apt_unattended_upgrades_blacklist:
#   - vim
#   - libc6
# apt_mails:
#   - root
#   - foo@dev.null
# apt_keys:
#   - keyserver: keyserver.ubuntu.com
#     id: 36A1D7869245C8950F966E92D8576A8BA88D21E9

# sets the amount of time the cache is valid
apt_cache_valid_time: 3600
# upgrade system: safe | full | dist
apt_upgrade: no
# packages to install
apt_packages: []
# remove packages that are no longer needed for dependencies
apt_autoremove: yes
# remove .deb files for packages no longer on your system
apt_autoclean: yes

# whether or not suggested packages should be installed.
apt_install_suggests: no
# do not install Recommended packages by default
apt_install_recommends: no
# allow 'apt-get autoremove' to remove recommended packages
apt_remove_recommends: no
# Enable the update/upgrade script
apt_periodic: yes
# Do “apt-get update” automatically every n-days (0=disable)
apt_update_package_lists: 1
# Do “apt-get upgrade –download-only” every n-days (0=disable)
apt_download_upgradeable_packages: 0
# Do “apt-get autoclean” every n-days (0=disable)
apt_auto_clean_interval: 0

# enable unattended-upgrades
apt_unattended_upgrades: yes
# list of packages to not update (regexp are supported)
apt_unattended_upgrades_blacklist: []
# Split the upgrade into the smallest possible chunks so that
# they can be interrupted with SIGUSR1. This makes the upgrade
# a bit slower but it has the benefit that shutdown while a upgrade
# is running is possible (with a small delay)
apt_unattended_upgrades_minimal_steps: no
# Send email to this address for problems or packages upgrades
# If empty or unset then no email is sent, make sure that you
# have a working mail setup on your system. A package that provides
# 'mailx' must be installed. E.g. "user@example.com"
apt_mails: []
# Set this value to "true" to get emails only on errors. Default
# is to always send a mail if Unattended-Upgrade::Mail is set
apt_unattended_upgrades_notify_error_only: yes
# Do automatic removal of new unused dependencies after the upgrade
# (equivalent to apt-get autoremove)
apt_unattended_upgrades_autoremove: yes
# Automatically reboot *WITHOUT CONFIRMATION*
# if the file /var/run/reboot-required is found after the upgrade
apt_unattended_upgrades_automatic_reboot: no
# If automatic reboot is enabled and needed, reboot at the specific
# time instead of immediately
# Values: now | 02:00 | ...
apt_unattended_upgrades_automatic_reboot_time: now

# remount file system: rootfs | tmpfs
#   tmpfs:  remount tmp before running if mounted noexec
#   rootfs: remount root filesystem r/w before running if mounted r/o
apt_remount_filesystem:
apt_remount_filesystems:

# repositories to register
apt_repositories: []
# gpg keys for external repositories
apt_keys: []
# HTTP proxy server (optional)
# apt_http_proxy_address:
# HTTP pipeline depth (optional)
# apt_http_pipeline_depth: 5

# Change Aptitudes solution costs, default is not to change anything
# Mirror https://lists.debian.org/543FF3BD.1020609@zen.co.uk
# apt_aptitude_solution_cost:
#   - priority
#   - removals
#   - canceled-actions
apt_aptitude_solution_cost: []


```


## Usage

This is an example playbook:

```yaml
---

- hosts: all
  roles:
    - weareinteractive.apt
  vars:
    apt_cache_valid_time: 7200
    apt_packages:
      - vim
      - tree
    apt_mails:
      - root
    apt_unattended_upgrades_notify_error_only: no


```


## Testing

```shell
$ git clone https://github.com/weareinteractive/ansible-apt.git
$ cd ansible-apt
$ make test
```

## Contributing
In lieu of a formal style guide, take care to maintain the existing coding style. Add unit tests and examples for any new or changed functionality.

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request

*Note: To update the `README.md` file please install and run `ansible-role`:*

```shell
$ gem install ansible-role
$ ansible-role docgen
```

## License
Copyright (c) We Are Interactive under the MIT license.
