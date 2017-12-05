from __future__ import print_function
from collections import namedtuple
import os
import subprocess
import sys

help_cache = os.path.join(os.path.dirname(__file__), 'help_cache')
available_help_caches = {
    'ansible -h': os.path.join(help_cache, 'ansible.txt')
}


def get_help_text(command):
    if command in available_help_caches:
        with open(available_help_caches[command]) as f:
            return f.read()
    else:
        return subprocess.check_output(command, shell=True)


def filtered_help_message(command, below_line, exclude_args, above_line=None):
    """

    :param command: command whose output should be parsed, e.g. 'ansible -h'
    :param below_line: line to trigger parsing;
        everything up to and including this line will be ignored
    :param exclude_args: list of args to exclude (short or long form)
        e.g. ['-m', '-b', '--become-user']
        fails hard if any of these args are not found
    :return:
    """
    large_indent = '                        '
    not_started, looking_for_arg, found_arg, traversing_arg_lines, eof = range(5)
    output = get_help_text(command)
    Section = namedtuple('Section', 'arg_names lines')

    class FSA(object):
        def __init__(self, lines):
            # arg_name : section_number
            self.remaining_lines = list(reversed(lines))
            self.section_index = {}
            self.sections = []
            self.working_section = None
            self.state = not_started

        def finalize_working_section(self):
            if self.working_section:
                for arg_name in self.working_section.arg_names:
                    self.section_index[arg_name] = len(self.sections)
                self.sections.append(self.working_section.lines)
            self.working_section = None

        def new_arg_section(self, arg_names):
            self.finalize_working_section()
            self.working_section = Section(arg_names, [])

        def new_fluff_section(self):
            self.finalize_working_section()
            self.working_section = Section((), [])

        def peek(self):
            try:
                return self.remaining_lines[-1]
            except IndexError:
                self.state = eof
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

    fsa = FSA(output.splitlines())
    while True:
        line = fsa.peek()
        if fsa.state is not not_started and line and line == above_line:
            fsa.state = eof

        if fsa.state is not_started:
            fsa.discard_line()
            if line == below_line:
                fsa.new_fluff_section()
                fsa.state = looking_for_arg
        elif fsa.state is looking_for_arg:
            if not line.startswith(large_indent) and line.lstrip().startswith('-'):
                fsa.state = found_arg
            else:
                fsa.consume_line()
        elif fsa.state is found_arg:
            # example line:
            # '    -s, --sudo          run operations with sudo (nopasswd) (deprecated, use'
            # parse ['-s', '--sudo']
            fsa.new_arg_section([
                part.strip().split(' ')[0].split('=')[0]
                for part in line.strip().split('  ')[0].split(',')
            ])
            fsa.consume_line()
            fsa.state = traversing_arg_lines
        elif fsa.state is traversing_arg_lines:
            if line.startswith(large_indent):
                fsa.consume_line()
            elif line.lstrip().startswith('-'):
                fsa.state = found_arg
            else:
                fsa.new_fluff_section()
                fsa.state = looking_for_arg
        elif fsa.state is eof:
            fsa.finalize_working_section()
            break

    return fsa.get_filtered_help_message(exclude_args)


def add_to_help_text(parser, additional_text):
    super_print_help = parser.print_help

    def print_help(file=None):
        if file is None:
            file = sys.stdout
        super_print_help(file)
        print(additional_text, file=file)
    parser.print_help = print_help
