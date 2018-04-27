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
    return re.search(r'[\[`\b]{}[\]`\b]'.format(re.escape(word)), text)


def fuzzy_contains(string, text):
    string = re.sub(r'\s*', ' ', string)
    string = string.strip().rstrip('.')
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


def test_all_arg_names_appear_in_docs():
    doc_text = _get_commands_doc()
    missing_args = set()
    for command_type in COMMAND_TYPES:
        for argument in command_type.arguments:
            if argument.include_in_docs and \
                    not contains_whole_word(argument.name_in_docs, doc_text):
                missing_args.add((command_type.command, argument.name_in_docs))

    assert not missing_args, "Missing arguments in {}:{}".format(
        COMMAND_DOC_PATH,
        ''.join(sorted('\n  {} (for {})'.format(argument, command)
                       for command, argument in missing_args))
    )
