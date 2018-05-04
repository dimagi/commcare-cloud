from __future__ import print_function

import cgi
import re

from ..argparse14 import RawTextHelpFormatter
from gettext import gettext as _

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commcare_cloud import make_parser


class _Section(RawTextHelpFormatter._Section):
    def format_help(self):
        formatted_help = super(_Section, self).format_help()

        if self.heading and formatted_help.strip().startswith(self.heading):
            # remove '<heading>:\n'
            formatted_help = formatted_help.strip()[len(self.heading) + 2:]
            return "### {}\n{}\n\n".format(self.heading.title(), formatted_help)
        else:
            return formatted_help


class MarkdownFormatter(RawTextHelpFormatter):
    _Section = _Section

    def __init__(self, *args, **kwargs):
        kwargs['width'] = kwargs.get('width', 125)
        super(MarkdownFormatter, self).__init__(*args, **kwargs)

    def _format_action_invocation(self, action):
        return "\n#### `{}`\n".format(
            super(MarkdownFormatter, self)._format_action_invocation(action))

    def _format_action(self, action):
        text = super(MarkdownFormatter, self)._format_action(action)
        return '\n'.join(line.strip() for line in text.splitlines())

    def _format_usage(self, usage, actions, groups, prefix):
        formatted_usage = super(MarkdownFormatter, self)._format_usage(usage, actions, groups, prefix)

        prefix = prefix or _('usage: ')
        if formatted_usage.startswith(prefix):
            return "**{}**\n```\n{}\n```\n".format(prefix.strip(), formatted_usage.strip()[len(prefix):])
        else:
            return formatted_usage

    def add_text(self, text):
        if text:
            text = cgi.escape(re.sub(r'({{|}})', r"{{ '\1' }}", text))
            text = self._reformat_help(text)
        return super(MarkdownFormatter, self).add_text(text)

    @staticmethod
    def _reformat_help(text):
        in_lines = text.strip().splitlines()

        if in_lines and in_lines[0].endswith(':'):
            class Parser(object):
                def __init__(self):
                    self.section = []
                    self.out_lines = []

                def parse(self, in_lines):
                    for line in in_lines:
                        if line.endswith(':'):
                            self.add_header(line[:-1])
                        else:
                            self.add_to_section(line)
                    self.shift_section()

                def add_header(self, header):
                    self.shift_section()
                    self.out_lines.extend(['### {}'.format(header)])

                def shift_section(self):
                    if self.section:
                        self.out_lines.append('```')
                        self.out_lines.extend(self.section)
                        self.out_lines.append('```')
                    self.section = []

                def add_to_section(self, line):
                    self.section.append(line)

                def get_output(self):
                    return '\n'.join(self.out_lines)

            parser = Parser()
            parser.parse(in_lines)
            return parser.get_output()
        else:
            return text


class MakeDocs(CommandBase):
    command = 'make-docs'
    help = "Build docs for commcare-cloud CLI tool"

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        parser, subparsers, commands = make_parser(
            available_envs=('<env>',),
            prog='commcare-cloud',
            formatter_class=MarkdownFormatter,
        )

        print('# `commcare-cloud`')
        parser.print_help()

        print("* TOC\n{:toc}")
        for command, subparser in subparsers.choices.items():
            print('## `{}`'.format(command))
            subparser.print_help()
