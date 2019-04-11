from __future__ import print_function

import cgi
import inspect
import os
import textwrap
from StringIO import StringIO

import jinja2

from ..argparse14 import RawTextHelpFormatter
from gettext import gettext as _

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commcare_cloud import make_command_parser, COMMAND_GROUPS


class _Section(RawTextHelpFormatter._Section):
    def format_help(self):
        formatted_help = super(_Section, self).format_help()

        if self.heading and formatted_help.strip().startswith(self.heading):
            # remove '<heading>:\n'
            formatted_help = formatted_help.strip()[len(self.heading) + 2:]
            return "{} {}\n{}\n\n".format(
                '#' * (self.formatter.header_level + 1),
                self.heading.title(), formatted_help)
        else:
            return formatted_help


class MarkdownFormatterBase(RawTextHelpFormatter):
    _Section = _Section

    header_level = None

    def __init__(self, *args, **kwargs):
        kwargs['width'] = kwargs.get('width', 125)
        kwargs['max_help_position'] = kwargs.get('max_help_position', 0)
        super(MarkdownFormatterBase, self).__init__(*args, **kwargs)

    def _format_action_invocation(self, action):
        return "\n{} `{}`\n".format(
            '#' * (self.header_level + 2),
            super(MarkdownFormatterBase, self)._format_action_invocation(action))

    def _format_action(self, action):
        return super(MarkdownFormatterBase, self)._format_action(action).lstrip(' ')

    def _format_usage(self, usage, actions, groups, prefix):
        formatted_usage = super(MarkdownFormatterBase, self)._format_usage(usage, actions, groups, prefix)

        prefix = prefix or _('usage: ')
        if formatted_usage.startswith(prefix):
            return "```\n{}\n```\n\n".format(
                '\n'.join(line[len(prefix):]
                          for line in formatted_usage.strip().splitlines()))
        else:
            return formatted_usage

    @staticmethod
    def wrap_lines(text):
        return '\n'.join('\n'.join(textwrap.wrap(line.strip(), 64))
                         for line in text.splitlines())

    @staticmethod
    def escape_html_outside_backticks(text):
        parts = text.split('`')
        for i in range(0, len(parts), 2):
            parts[i] = cgi.escape(parts[i])
        return '`'.join(parts)

    def _stick_first_line_above_last_usage_and_return_the_rest(self, text):
        """
        stick the first line of :text: before the usage
        and return the rest if condition met, otherwise just return all the text.

        to trigger the interesting behavior both of the following must be true
        - the previous item added must be a usage
        - text must be only one line OR text must have a blank line after the first line

        """
        if text and self._current_section.items and self._current_section.items[-1][0] == self._format_usage:
            lines = inspect.cleandoc(text).splitlines()
            if len(lines) == 1 or lines[1] == '':
                last_usage = self._current_section.items.pop(-1)
                head = lines[0]
                tail = '\n'.join(lines[2:])
                super(MarkdownFormatterBase, self).add_text(head)
                self._current_section.items.append(last_usage)
                return tail
        return text

    def add_text(self, text):
        text = self._stick_first_line_above_last_usage_and_return_the_rest(text)
        super(MarkdownFormatterBase, self).add_text(text)

    def _format_text(self, text):
        text = text.replace("{{", "{{ '{{' }}")
        text = self.escape_html_outside_backticks(text)
        in_lines = text.strip().splitlines()

        if in_lines and in_lines[0].endswith(':') \
                and any(line.startswith('  ') for line in in_lines):
            class Parser(object):
                def __init__(self, formatter):
                    self.section = []
                    self.out_lines = []
                    self.formatter = formatter

                def parse(self, in_lines):
                    for line in in_lines:
                        if line.endswith(':'):
                            self.add_header(line[:-1])
                        else:
                            self.add_to_section(line)
                    self.shift_section()

                def add_header(self, header):
                    self.shift_section()
                    self.out_lines.extend(['{} {}'.format('#' * (self.formatter.header_level + 1), header)])

                def shift_section(self):
                    if self.section:
                        self.out_lines.append('```')
                        self.out_lines.extend(self.section)
                        self.out_lines.append('```')
                    self.section = []

                def add_to_section(self, line):
                    self.section.append(line)

                def get_output(self):
                    return '\n'.join(self.out_lines) + '\n'

            parser = Parser(formatter=self)
            parser.parse(in_lines)
            text = parser.get_output()
        else:
            text = text.replace('Example:\n', '##### Example\n')
        return super(MarkdownFormatterBase, self)._format_text(text)


class MarkdownFormatter(MarkdownFormatterBase):
    header_level = 1

    def __init__(self, *args, **kwargs):
        self.skip_actions = kwargs.pop('skip_actions', ())
        super(MarkdownFormatter, self).__init__(*args, **kwargs)

    def _format_action(self, action):
        if action.__class__.__name__ == '_SubParsersAction':
            return ''
        else:
            return super(MarkdownFormatter, self)._format_action(action)


class SubparserMarkdownFormatter(MarkdownFormatterBase):
    header_level = 4


class MakeDocs(CommandBase):
    command = 'make-docs'
    help = "Build docs for commcare-cloud CLI tool"

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

        def do_print_help(parser):
            """Capture output of parser.print_help()"""
            string_io = StringIO()
            parser.print_help(file=string_io)
            return string_io.getvalue()

        j2.filters['print_help'] = do_print_help

        parser, subparsers, commands = make_command_parser(
            available_envs=None,
            prog='commcare-cloud',
            formatter_class=MarkdownFormatter,
            subparser_formatter_class=SubparserMarkdownFormatter,
            add_help=False,
            for_docs=True,
        )

        subparsers_by_group = [
            (group, [(cmd, subparsers.choices[cmd.command]) for cmd in command_types])
            for group, command_types in COMMAND_GROUPS.items()
        ]
        template = j2.get_template('commands.md.j2')
        print(template.render(parser=parser, subparsers_by_group=subparsers_by_group,
                              commands=commands), end='')

