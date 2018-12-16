from __future__ import print_function
from __future__ import absolute_import

import jsonobject

import jinja2
import os
import re
import sys
from io import open

import yaml

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


def compile_changelog():
    # Parse the contents of the changelog dir
    changelog_contents = []
    changelog_dir = 'changelog'
    sorted_files = _sort_files(changelog_dir)
    for change_file_name in sorted_files:
        entry = load_changelog_entry(os.path.join(changelog_dir, change_file_name))
        verify_changelog_markdown_exists(changelog_dir, entry)
        changelog_contents.append(entry)
    return changelog_contents


def verify_changelog_markdown_exists(changelog_dir, entry):
    changelog_md = os.path.join("docs", changelog_dir, entry["filename"])
    if not os.path.exists(changelog_md):
        print("error: changelog details not found: %s\nthis file should "
              "contain any details and steps necessary to bring an "
              "environment up to date for the described changes" %
              changelog_md, file=sys.stderr)
        sys.exit(1)


def load_changelog_entry(path):
    try:
        with open(path) as f:
            change_yaml = yaml.load(f)
            change_yaml['filename'] = re.sub(r'\.yml$', '.md', path.split('/')[-1])
            # yaml.load already parses dates, using this instead of ChangelogEntry.wrap
            return ChangelogEntry(**change_yaml)
    except Exception:
        print("Error parsing the file {}.".format(path), file=sys.stderr)
        raise


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


class MakeChangelogIndex(CommandBase):
    command = 'make-changelog-index'
    help = "Build the commcare-cloud CLI tool's changelog index"
    arguments = ()

    def run(self, args, unknown_args):
        j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)), keep_trailing_newline=True)

        changelog_contents = compile_changelog()

        template = j2.get_template('changelog-index.md.j2')
        print(template.render(changelog_contents=changelog_contents).rstrip())
