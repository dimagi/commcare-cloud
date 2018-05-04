from __future__ import print_function

import cgi
import os
import re
import textwrap
from StringIO import StringIO

import jinja2

from ..argparse14 import RawTextHelpFormatter
from gettext import gettext as _

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commcare_cloud import make_parser, COMMAND_TYPES


class _Section(RawTextHelpFormatter._Section):
    def format_help(self):
        formatted_help = super(_Section, self).format_help()

        if self.heading and formatted_help.strip().startswith(self.heading):
            # remove '<heading>:\n'
            formatted_help = formatted_help.strip()[len(self.heading) + 2:]
            return "{} {}\n{{:.no_toc}}\n{}\n\n".format(
                '#' * (self.formatter.header_level + 1),
                self.heading.title(), formatted_help)
        else:
            return formatted_help


class MarkdownFormatterBase(RawTextHelpFormatter):
    _Section = _Section

    header_level = None

    def __init__(self, *args, **kwargs):
        kwargs['width'] = kwargs.get('width', 125)
        super(MarkdownFormatterBase, self).__init__(*args, **kwargs)

    def _format_action_invocation(self, action):
        return "\n{} `{}`\n{{:.no_toc}}\n".format(
            '#' * (self.header_level + 2),
            super(MarkdownFormatterBase, self)._format_action_invocation(action))

    def _format_action(self, action):
        text = super(MarkdownFormatterBase, self)._format_action(action)
        return self.wrap_lines(text)

    def _format_usage(self, usage, actions, groups, prefix):
        formatted_usage = super(MarkdownFormatterBase, self)._format_usage(usage, actions, groups, prefix)

        prefix = prefix or _('usage: ')
        if formatted_usage.startswith(prefix):
            return "```\n{}\n```\n\n".format(formatted_usage.strip()[len(prefix):])
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

    def add_text(self, text):
        if text:
            text = re.sub(r'({{|}})', r"{{ '\1' }}", text)
            text = self.escape_html_outside_backticks(text)
            text = self._reformat_help(text)
        return super(MarkdownFormatterBase, self).add_text(text)

    def _reformat_help(self, text):
        in_lines = text.strip().splitlines()

        if in_lines and in_lines[0].endswith(':'):
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
                    self.out_lines.extend(['{} {}'.format('#' * (self.formatter.header_level + 1), header),
                                           '{:.no_toc}'])

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
            return parser.get_output()
        else:
            return text


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
    header_level = 3


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

        parser, subparsers, commands = make_parser(
            available_envs=('<env>',),
            prog='commcare-cloud',
            formatter_class=MarkdownFormatter,
            subparser_formatter_class=SubparserMarkdownFormatter,
            add_help=False,
            for_docs=True,
        )
        subparsers = [(cmd.command, subparsers.choices[cmd.command]) for cmd in COMMAND_TYPES]
        template = j2.get_template('commands.md.j2')
        print(template.render(parser=parser, subparsers=subparsers, commands=commands), end='')
