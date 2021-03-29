from __future__ import print_function
from __future__ import absolute_import

from __future__ import unicode_literals

from datetime import datetime

import jsonobject

import jinja2
import os
import re
import sys
from io import open

import yaml
from clint.textui import puts

from commcare_cloud.colors import color_error
from commcare_cloud.commands.command_base import CommandBase, Argument

GitVersionProperty = jsonobject.StringProperty
MarkdownProperty = jsonobject.StringProperty


class ChangelogEntry(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    # filename is the only property that is populated from outside the yaml file
    filename = jsonobject.StringProperty()

    title = jsonobject.StringProperty()

    key = jsonobject.StringProperty()

    # Date when this change was added (purely for informational purposes)
    date = jsonobject.DateProperty()

    optional_per_env = jsonobject.BooleanProperty()

    # Min version of HQ that MUST be deployed before this change can be rolled out
    min_commcare_version = GitVersionProperty()

    # Max version of HQ that can be deployed before this change MUST be rolled out
    max_commcare_version = GitVersionProperty()

    # Description of the change
    # This will be shown as a sort of "preview" in the index
    context = MarkdownProperty()

    # Details of the change
    details = MarkdownProperty()

    # Steps to update
    update_steps = MarkdownProperty()


def compile_changelog():
    # Parse the contents of the changelog dir
    changelog_contents = []
    changelog_dir = 'changelog'
    sorted_files = _sort_files(changelog_dir)
    for change_file_name in sorted_files:
        if change_file_name.endswith('.yml'):
            changelog_contents.append(load_changelog_entry(os.path.join(changelog_dir, change_file_name)))
    return changelog_contents


def load_changelog_entry(path):
    try:
        with open(path, encoding='utf-8') as f:
            change_yaml = yaml.safe_load(f)
            change_yaml['filename'] = re.sub(r'\.yml$', '.md', path.split('/')[-1])
            # yaml.safe_load already parses dates, using this instead of ChangelogEntry.wrap
            return ChangelogEntry(**change_yaml)
    except Exception:
        print("Error parsing the file {}.".format(path), file=sys.stderr)
        raise


def _sort_files(directory):
    """
    Sorts filenames by descending alphanumeric order, userful for organizing the changelog index.md
    """
    return sorted(os.listdir(directory), reverse=True)


class MakeChangelogIndex(CommandBase):
    command = 'make-changelog-index'
    help = "Build the commcare-cloud CLI tool's changelog index"
    arguments = ()

    def run(self, args, unknown_args):
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), keep_trailing_newline=True)

        changelog_contents = compile_changelog()

        template = j2.get_template('changelog-index.md.j2')
        print(template.render(changelog_contents=changelog_contents).rstrip())


class MakeChangelog(CommandBase):
    command = 'make-changelog'
    help = "Build the commcare-cloud CLI tool's individual changelog files"
    arguments = (
        Argument(dest='changelog_yml', help="""Path to the yaml changelog file"""),
    )

    def run(self, args, unknown_args):
        changelog_yml = args.changelog_yml
        ordinal = int(changelog_yml.split('/')[-1].split('-')[0])
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), keep_trailing_newline=True)

        changelog_entry = load_changelog_entry(changelog_yml)
        template = j2.get_template('changelog.md.j2')

        text = template.render(changelog_entry=changelog_entry, ordinal=ordinal)
        text = text.rstrip().replace('{{', "{{ '{{' }}")
        print(text)


class NewChangelog(CommandBase):
    command = 'new-changelog'
    help = "Create a blank changelog"
    arguments = (
        Argument(dest="name", nargs="?", help="""Name of the changelog"""),
    )

    def run(self, args, unknown_args):
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), keep_trailing_newline=True)

        changelog_dir = 'changelog'
        for filename in _sort_files(changelog_dir):
            if filename.endswith(".yml"):
                last_log = filename
                break
        else:
            puts(color_error("Unable to find last changelog file. Please create a changelog manually."))
            return 1

        last_index = int(re.search(r"^(\d+)", last_log).group())

        name = args.name
        date = datetime.utcnow()
        if not name:
            name = "auto {}".format(date.strftime("%Y%m%d_%H%M"))

        name = re.sub("[\n\r\t]", " ", name)
        key = name.replace(" ", "_")
        file_name = "{:04d}-{}.yml".format(last_index + 1, key)

        template = j2.get_template('changelog-template.yml.j2')
        path = os.path.join(changelog_dir, file_name)
        with open(path, 'w') as f:
            f.write(template.render(name=name, key=key, date=date.strftime("%Y-%m-%d")).rstrip())

        print("Changelog created at {}".format(path))
