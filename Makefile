CHANGELOG_YML = $(wildcard changelog/*.yml)
CHANGELOG_MD = $(patsubst %.yml, docs/%.md, $(CHANGELOG_YML))
autogen = src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt docs/commcare-cloud/commands/index.md docs/changelog/index.md $(CHANGELOG_MD)
all : $(autogen)

PIP_COMPILE = pip-compile --output-file requirements.txt setup.py requirements*.in

ANSIBLE_ENV=COLUMNS=80
src/commcare_cloud/help_cache/ansible.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible.txt:
	$(ANSIBLE_ENV) ansible -h > src/commcare_cloud/help_cache/ansible.txt

src/commcare_cloud/help_cache/ansible-playbook.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible-playbook.txt:
	$(ANSIBLE_ENV) ansible-playbook -h > src/commcare_cloud/help_cache/ansible-playbook.txt

docs/commcare-cloud/commands/index.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > docs/commcare-cloud/commands/index.md



docs/changelog/%.md : changelog/%.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog $< > $@

docs/changelog/index.md : changelog/*.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog-index > docs/changelog/index.md

requirements: requirements-*.in setup.py
	$(PIP_COMPILE)

upgrade-requirements: requirements-*.in setup.py
	$(PIP_COMPILE) --upgrade

clean:
	rm $(autogen)
