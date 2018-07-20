all : src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt docs/commcare-cloud/commands/index.md docs/changelog/index.md

src/commcare_cloud/help_cache/ansible.txt:
	ansible -h | sed "s|${HOME}|~|g" > src/commcare_cloud/help_cache/ansible.txt

src/commcare_cloud/help_cache/ansible-playbook.txt:
	ansible-playbook -h | sed "s|${HOME}|~|g" > src/commcare_cloud/help_cache/ansible-playbook.txt

docs/commcare-cloud/commands/index.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > docs/commcare-cloud/commands/index.md

===============
docs/changelog/index.md : src/commcare_cloud/* src/commcare_cloud/*/* src/commcare_cloud/*/*/*
	manage-commcare-cloud make-docs > docs/changelog/index.md
===============

requirements: requirements-*.in setup.py
	pip-compile --output-file requirements.txt setup.py requirements*.in --upgrade

clean:
	rm docs/commcare-cloud/commands/index.md docs/changelog/index.md src/commcare_cloud/help_cache/ansible.txt src/commcare_cloud/help_cache/ansible-playbook.txt
