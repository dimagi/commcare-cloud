from __future__ import print_function
from __future__ import absolute_import

import jinja2
import os
import re
import sys
from commcare_cloud.commands.command_base import CommandBase


def compile_changelog():
    # Parse the contents of the changelog dir
    changelog_contents = []
    files_to_ignore = ['0000-changelog.md', 'index.md']
    changelog_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'docs', 'changelog')
    sorted_files = _sort_files(changelog_dir)
    for change_file_name in sorted_files:
        if change_file_name not in files_to_ignore:
            try:
                _parse_changelog_file(changelog_contents, changelog_dir, change_file_name)
            except Exception:
                print("Error parsing the file {}.".format(change_file_name), file=sys.stderr)
                raise
    return changelog_contents


def _parse_changelog_file(changelog_contents, changelog_dir, change_file_name):
    with open(os.path.join(changelog_dir, change_file_name)) as change_file:
        change_context = ''
        change_date = ''
        in_change_context = False
        change_action_required = False
        reached_details_line = False
        for line_number, line in enumerate(change_file):
            if line_number == 0:
                change_summary = re.search('(?<=\.).*', line).group().strip()
            if '**Date:**' in line:
                change_date = line.split('**Date:**')[1].strip()
            if '**Optional per env:**' in line:
                option = line.split('**Optional per env:**')[1].strip().lower()
                if "no" in option:
                    change_action_required = True
            if '## Details' in line:
                in_change_context = False
                reached_details_line = True
            if in_change_context:
                change_context += line
            if '## Change Context' in line:
                in_change_context = True
        assert (
            change_file_name and change_context and change_date and change_summary and
            change_action_required is not None and reached_details_line
        ), "The following variables shouldn't be falsely during parse:\n{}".format('\n'.join([
            "{}: {!r}".format(name, value)
            for name, value in [('change_file_name', change_file_name),
            ('change_context', change_context),
            ('change_date', change_date),
            ('change_summary', change_summary),
            ('change_action_required', change_action_required is not None),
            ('reached_details_line', reached_details_line)]
            if value is None
        ]))
        this_changelog = {'filename': change_file_name,
                          'context': change_context.strip(),
                          'date': change_date,
                          'summary': change_summary,
                          'action_required': change_action_required}

    changelog_contents.append(this_changelog)


def _sort_files(directory):
    """
    Sorts filenames by descending alphanumeric order, userful for organizing the changelog index.md
    """
    def _natural_keys(text):
        retval = [int(c) if c.isdigit() else c for c in text[:4]]
        return retval
    unsorted_files = os.listdir(directory)
    unsorted_files.sort(key=_natural_keys, reverse=True)
    return unsorted_files


class MakeChangelog(CommandBase):
    command = 'make-changelog-index'
    help = "Build the commcare-cloud CLI tool's changelog"

    def make_parser(self):
        pass

    def run(self, args, unknown_args):
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), keep_trailing_newline=True)

        changelog_contents = compile_changelog()

        template = j2.get_template('changelog.md.j2')
        print(template.render(changelog_contents=changelog_contents))
