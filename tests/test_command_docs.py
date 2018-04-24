from __future__ import unicode_literals
import os
import re

from memoized import memoized

from commcare_cloud.commcare_cloud import COMMAND_TYPES


COMMAND_DOC_PATH = 'docs/commcare-cloud/commands/index.md'


@memoized
def _get_commands_doc():
    filename = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', COMMAND_DOC_PATH))
    with open(filename) as f:
        return f.read()


def contains_whole_word(word, text):
    return re.search(r'\b{}\b'.format(re.escape(word)), text)


def contains_but_for_whitespace(string, text):
    string = re.sub(r'\s*', ' ', string)
    text = re.sub(r'\s*', ' ', text)

    return string in text


def test_all_commands_appear_in_docs():
    doc_text = _get_commands_doc()
    missing_commands = set()
    for command_type in COMMAND_TYPES:
        if not contains_whole_word(command_type.command, doc_text):
            missing_commands.add(command_type.command)
    assert not missing_commands, "Missing commands in {}: {}".format(
        COMMAND_DOC_PATH,
        ', '.join(sorted(missing_commands))
    )


def test_all_aliases_appear_in_docs():
    doc_text = _get_commands_doc()
    missing_aliases = set()
    for command_type in COMMAND_TYPES:
        for alias in command_type.aliases:
            if not contains_whole_word(alias, doc_text):
                missing_aliases.add((command_type.command, alias))
    assert not missing_aliases, "Missing aliases in {}: {}".format(
        COMMAND_DOC_PATH,
        ', '.join(sorted('{} (for {})'.format(alias, command)
                         for command, alias in missing_aliases))
    )


def test_all_help_strings_appear_in_docs():
    doc_text = _get_commands_doc()
    missing_help_strings = set()
    for command_type in COMMAND_TYPES:
        if not contains_but_for_whitespace(command_type.help, doc_text):
            missing_help_strings.add(command_type.command)

    assert not missing_help_strings, "Missing help strings in {}: {}".format(
        COMMAND_DOC_PATH,
        ', '.join(sorted(missing_help_strings))
    )
