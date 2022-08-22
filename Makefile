CHANGELOG_YML = $(wildcard changelog/*.yml)
CHANGELOG_MD = $(patsubst %.yml, hosting_docs/source/%.md, $(CHANGELOG_YML))
autogen = src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt hosting_docs/source/reference/1-commcare-cloud/commands.md hosting_docs/source/changelog/index.md src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id $(CHANGELOG_MD)
all : $(autogen)

REQUIREMENTS=requirements.txt
PIP_COMPILE = pip-compile --output-file ${REQUIREMENTS} setup.py

ANSIBLE_ENV=COLUMNS=80
src/commcare_cloud/help_cache/ansible.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible.txt:
	$(ANSIBLE_ENV) ansible -h | sed 's/^optional arguments:/options:/' > src/commcare_cloud/help_cache/ansible.txt

src/commcare_cloud/help_cache/ansible-playbook.txt: export ANSIBLE_CONFIG=src/commcare_cloud/ansible/ansible.cfg
src/commcare_cloud/help_cache/ansible-playbook.txt:
	$(ANSIBLE_ENV) ansible-playbook -h | sed 's/^optional arguments:/options:/' > src/commcare_cloud/help_cache/ansible-playbook.txt

hosting_docs/source/reference/1-commcare-cloud/commands.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > hosting_docs/source/reference/1-commcare-cloud/commands.md


hosting_docs/source/changelog/%.md : changelog/%.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog $< > $@

hosting_docs/source/changelog/index.md : changelog/*.yml src/commcare_cloud/manage_commcare_cloud/*
	manage-commcare-cloud make-changelog-index > hosting_docs/source/changelog/index.md

requirements: setup.py
	$(PIP_COMPILE)

upgrade-requirements: setup.py
	$(PIP_COMPILE) --upgrade

src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id:
	curl https://gist.githubusercontent.com/lbernail/d851e5b06eb32180a4b8ead2ce4f45db/raw/07772083fa1c2e567ed422eb401ac7783487d1c7/ebsnvme-id \
	  > src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id.raw
	echo "3437393d3f0ba1088bc18db5bdc5e73d2cedd96fd39a086f2c5e5f061b955f58  src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id.raw" \
	  | shasum -a256 -c - \
	  && mv src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id.raw src/commcare_cloud/ansible/roles/ebsnvme/files/_vendor/ebsnvme-id

clean:
	rm -f $(autogen)
