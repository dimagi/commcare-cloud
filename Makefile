autogen = src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt docs/commcare-cloud/commands/index.md docs/changelog/index.md
all : $(autogen)


# The length of the home directory affects
# how help text gets wrapped in ansible/ansible-playbook -h output.
# Pick a standard (but arbitrary) value for $HOME to be used across all environments.
# Make it short but unlikely to occur otherwise, so that we can safely find/replace it with ~.
# (Directly using escaped '~' does not work.)
STANDARD_HOME=/!

src/commcare_cloud/help_cache/ansible.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible.txt:
	COLUMNS=80 HOME="${STANDARD_HOME}" ansible -h | sed "s|${STANDARD_HOME}|~|g" | sed "s|`pwd`|.|g" > src/commcare_cloud/help_cache/ansible.txt

src/commcare_cloud/help_cache/ansible-playbook.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible-playbook.txt:
	COLUMNS=80 HOME="${STANDARD_HOME}" ansible-playbook -h | sed "s|${STANDARD_HOME}|~|g" | sed "s|`pwd`|.|g" > src/commcare_cloud/help_cache/ansible-playbook.txt

docs/commcare-cloud/commands/index.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > docs/commcare-cloud/commands/index.md

docs/changelog/index.md : docs/changelog/0*.md src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog-index > docs/changelog/index.md

requirements: requirements-*.in setup.py
	pip-compile --output-file requirements.txt setup.py requirements*.in

upgrade-requirements: requirements-*.in setup.py
	pip-compile --output-file requirements.txt setup.py requirements*.in --upgrade

clean:
	rm $(autogen)
