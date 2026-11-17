"""Non-interactive pause for Molecule.

Molecule runs ansible-playbook with the terminal's stdin, so a `pause` prompt
blocks a local run and gets empty input in CI. Setting `user_input` with -e
doesn't work either: `failed_when` sees the registered result, not the extra
var.

This plugin is next to converge.yml, so it overrides the builtin `pause`.
When `molecule_pause_user_input` is set, it shows the prompt and returns that
value as `user_input`. Otherwise it runs the real pause.
"""
from ansible.plugins.action.pause import ActionModule as PauseActionModule
from ansible.utils.display import Display

display = Display()


class ActionModule(PauseActionModule):

    def run(self, tmp=None, task_vars=None):
        if task_vars is None or 'molecule_pause_user_input' not in task_vars:
            return super().run(tmp, task_vars)

        name = self._task.get_name().strip()
        prompt = self._task.args.get('prompt', '')
        user_input = self._templar.template(task_vars['molecule_pause_user_input'])
        display.display(f"[{name}]\n{prompt}: {user_input}")
        return dict(
            changed=False,
            rc=0,
            stderr='',
            stdout='',
            user_input=user_input,
        )
