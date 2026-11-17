"""Non-interactive pause for Molecule.

Molecule runs ansible-playbook with the terminal's stdin, so a `pause` prompt
blocks a local run and gets empty input in CI. Setting `user_input` with -e
doesn't work either: `failed_when` sees the registered result, not the extra
var.

This plugin is next to converge.yml, so it overrides the builtin `pause`. It
shows the prompt and returns `molecule_pause_user_input` as `user_input`.
"""
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

display = Display()


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        if task_vars is None or 'molecule_pause_user_input' not in task_vars:
            raise AnsibleActionFail(
                "set molecule_pause_user_input in the scenario's inventory")

        name = self._task.get_name().strip()
        prompt = self._task.args.get('prompt', '')
        user_input = self._templar.template(task_vars['molecule_pause_user_input'])
        display.display(f"[{name}]\n{prompt}: {user_input}")
        result.update(
            changed=False,
            rc=0,
            stderr='',
            stdout='',
            user_input=user_input,
        )
        return result
