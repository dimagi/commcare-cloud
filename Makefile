CHANGELOG_YML = $(wildcard changelog/*.yml)
CHANGELOG_MD = $(patsubst %.yml, docs/%.md, $(CHANGELOG_YML))
autogen = src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt docs/commcare-cloud/commands/index.md docs/changelog/index.md $(CHANGELOG_MD)
all : $(autogen)

PIP_COMPILE = pip-compile --output-file requirements.txt setup.py requirements*.in

# The length of the home directory affects
# how help text gets wrapped in ansible/ansible-playbook -h output.
# Pick a standard (but arbitrary) value for $HOME to be used across all environments.
# Make it short but unlikely to occur otherwise, so that we can safely find/replace it with ~.
# (Directly using escaped '~' does not work.)
STANDARD_HOME=/tmp
# ANSIBLE_LIBRARY cannot be set to a relative path,
# because it gets expanded to an absolute path.
# Instead we prefix it with a fake absolute prefix we can replace later in ansible -h output.
STANDARD_ANSIBLE_DIR=~/.x
# This pulls the value of library from ansible.cfg, and replaces ./ with the fake prefix
ANSIBLE_LIBRARY=$$(grep 'library = ' $$ANSIBLE_CONFIG | sed -e 's|library = ||g' -e 's|\.|$(STANDARD_ANSIBLE_DIR)|')
ANSIBLE_ENV=ANSIBLE_LIBRARY=$(ANSIBLE_LIBRARY) COLUMNS=80 HOME="${STANDARD_HOME}"
REPLACE_PATHS=sed -e "s|${STANDARD_HOME}|~|g" -e "s|$(STANDARD_ANSIBLE_DIR)|./src/commcare_cloud/ansible|g"

src/commcare_cloud/help_cache/ansible.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible.txt:
	$(ANSIBLE_ENV) ansible -h | $(REPLACE_PATHS) > src/commcare_cloud/help_cache/ansible.txt

src/commcare_cloud/help_cache/ansible-playbook.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible-playbook.txt:
	$(ANSIBLE_ENV) ansible-playbook -h | $(REPLACE_PATHS) > src/commcare_cloud/help_cache/ansible-playbook.txt

docs/commcare-cloud/commands/index.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > docs/commcare-cloud/commands/index.md



docs/changelog/%.md : changelog/%.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog $< $@

docs/changelog/index.md : changelog/*.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog-index > docs/changelog/index.md

requirements: requirements-*.in setup.py
	$(PIP_COMPILE)

upgrade-requirements: requirements-*.in setup.py
	$(PIP_COMPILE) --upgrade

clean:
	rm $(autogen)
