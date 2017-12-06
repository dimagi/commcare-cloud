from __future__ import print_function
from collections import namedtuple
import os
import subprocess
import sys

_HELP_CACHE = os.path.join(os.path.dirname(__file__), 'help_cache')
_AVAILABLE_HELP_CACHES = {
    'ansible -h': os.path.join(_HELP_CACHE, 'ansible.txt'),
    'ansible-playbook -h': os.path.join(_HELP_CACHE, 'ansible-playbook.txt'),
}


def _get_help_text(command):
    if command in _AVAILABLE_HELP_CACHES:
        with open(_AVAILABLE_HELP_CACHES[command]) as f:
            return f.read().replace("/home/travis", os.path.expanduser('~'))
    else:
        return subprocess.check_output(command, shell=True)


_LARGE_INDENT = '                        '


class _States(object):
    NOT_STARTED, LOOKING_FOR_ARG, FOUND_ARG, TRAVERSING_ARG_LINES, FOUND_EOF = range(5)

_Section = namedtuple('Section', 'arg_names lines')


class _ParseState(object):
    def __init__(self, lines):
        # arg_name : section_number
        self.remaining_lines = list(reversed(lines))
        self.section_index = {}
        self.sections = []
        self.working_section = None
        self.state = _States.NOT_STARTED

    def set_state(self, state):
        self.state = state

    def finalize_working_section(self):
        if self.working_section:
            for arg_name in self.working_section.arg_names:
                self.section_index[arg_name] = len(self.sections)
            self.sections.append(self.working_section.lines)
        self.working_section = None

    def new_arg_section(self, arg_names):
        self.finalize_working_section()
        self.working_section = _Section(arg_names, [])

    def new_fluff_section(self):
        self.finalize_working_section()
        self.working_section = _Section((), [])

    def peek(self):
        try:
            return self.remaining_lines[-1]
        except IndexError:
            self.state = _States.FOUND_EOF
            return None

    def consume_line(self):
        self.working_section.lines.append(self.remaining_lines.pop())

    def discard_line(self):
        self.remaining_lines.pop()

    def get_filtered_help_message(self, exclude_args):
        exclude_section_numbers = {self.section_index[arg_name]
                                   for arg_name in exclude_args}

        def yield_lines():
            for i, section in enumerate(self.sections):
                if i not in exclude_section_numbers:
                    for line in section:
                        yield line

        return '\n'.join(yield_lines())


def _parse_arg_line(line):
    """
    pull out the arg names from a line of CLI help text introducing args

    >>> _parse_arg_line('    -s, --sudo          run operations with sudo (nopasswd) (deprecated, use')
    ['-s', '--sudo']

    """
    return [
        part.strip().split(' ')[0].split('=')[0]
        for part in line.strip().split('  ')[0].split(',')
    ]


def filtered_help_message(command, below_line, exclude_args, above_line=None):
    """
    filter a CLI help message by start and end line and args to exclude

    parses in the style of a finite state automaton (FSA),
    though it's probably not a pure FSA.
    In the parsing model used here,
    each line is an input that is used to determine then next state.
    States are defined in the _States above,
    and _ParseState is used to keep track of input to be consumed, state, and output.

    :param command: command whose output should be parsed, e.g. 'ansible -h'
    :param below_line: line to trigger parsing;
        everything up to and including this line will be ignored
    :param exclude_args: list of args to exclude (short or long form)
        e.g. ['-m', '-b', '--become-user']
        fails hard if any of these args are not found
    :param above_line: line that triggers end of parsing
        everything after and including this line will be ignored
    :return:
    """
    output = _get_help_text(command)

    p = _ParseState(output.splitlines())

    while True:
        line = p.peek()
        if p.state is not _States.NOT_STARTED and line and line == above_line:
            p.set_state(_States.FOUND_EOF)

        if p.state is _States.NOT_STARTED:
            p.discard_line()
            if line == below_line:
                p.new_fluff_section()
                p.set_state(_States.LOOKING_FOR_ARG)

        elif p.state is _States.LOOKING_FOR_ARG:
            if line.startswith(_LARGE_INDENT):
                p.consume_line()
            if line.lstrip().startswith('-'):
                p.set_state(_States.FOUND_ARG)
            else:
                p.consume_line()

        elif p.state is _States.FOUND_ARG:
            p.new_arg_section(_parse_arg_line(line))
            p.consume_line()
            p.set_state(_States.TRAVERSING_ARG_LINES)

        elif p.state is _States.TRAVERSING_ARG_LINES:
            if line.startswith(_LARGE_INDENT):
                p.consume_line()
            elif line.lstrip().startswith('-'):
                p.set_state(_States.FOUND_ARG)
            else:
                p.new_fluff_section()
                p.set_state(_States.LOOKING_FOR_ARG)

        elif p.state is _States.FOUND_EOF:
            p.finalize_working_section()
            break

    return p.get_filtered_help_message(exclude_args)


def add_to_help_text(parser, additional_text):
    super_print_help = parser.print_help

    def print_help(file=None):
        if file is None:
            file = sys.stdout
        super_print_help(file)
        print(additional_text, file=file)
    parser.print_help = print_help
