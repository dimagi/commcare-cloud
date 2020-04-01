# coding=utf-8
from __future__ import absolute_import
from clint.textui import colored


def colored_none(string, *args, **kwargs):
    return string


color_code = colored.cyan  # for underlying bash commands that are being run
color_error = colored.red  # for errors, things that have gone wrong (irrecoverably)
color_highlight = colored.yellow  # for highlighting the thing the user is most likely to use
color_notice = colored.yellow  # for notices, "PSAs", or important FYIs to the user
color_prompt = colored_none  # for prompts requiring a user response
color_success = colored.green  # for success messages
color_summary = colored.blue  # for useful summarizing output in a sea of verbose output
color_warning = colored.magenta  # for warnings about things likely to be problematic
color_link = colored.blue  # for hyperlinks

# for diffs
color_added = colored.green
color_removed = colored.red
color_unchanged = colored.cyan
color_changed = colored.yellow


# For future reference here are the ansible colors
#
# https://docs.ansible.com/ansible/latest/reference_appendices/config.html?highlight=colors
#
# COLOR_CHANGED: yellow  # Defines the color to use on ‘Changed’ task status
# COLOR_CONSOLE_PROMPT: white  # Defines the default color to use for ansible-console
# COLOR_DEBUG: dark gray  # Defines the color to use when emitting debug messages
# COLOR_DEPRECATE: purple  # Defines the color to use when emitting deprecation messages
# COLOR_DIFF_ADD: green  # Defines the color to use when showing added lines in diffs
# COLOR_DIFF_LINES: cyan  # Defines the color to use when showing diffs
# COLOR_DIFF_REMOVE: red  # Defines the color to use when showing removed lines in diffs
# COLOR_ERROR: red  # Defines the color to use when emitting error messages
# COLOR_HIGHLIGHT: white  # Defines the color to use for highlighting
# COLOR_OK: green  # Defines the color to use when showing ‘OK’ task status
# COLOR_SKIP: cyan  # Defines the color to use when showing ‘Skipped’ task status
# COLOR_UNREACHABLE: bright red  # Defines the color to use on ‘Unreachable’ status
# COLOR_VERBOSE: blue  # Defines the color to use when emitting verbose messages.
#                      # i.e those that show with ‘-v’s.
# COLOR_WARN: bright purple  # Defines the color to use when emitting warning messages
