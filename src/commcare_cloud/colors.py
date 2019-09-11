from clint.textui import colored


def colored_none(string, *args, **kwargs):
    return string


color_command_log = colored.cyan  # for underlying bash commands that are being run
color_error = colored.red  # for errors, things that have gone wrong (irrecoverably)
color_highlight = colored.yellow  # for highlighting the thing the user is most likely to use
color_notice = colored.yellow  # for notices, "PSAs", or important FYIs to the user
color_prompt = colored_none  # for prompts requiring a user response
color_success = colored.green  # for success messages
color_summary = colored.blue  # for useful summarizing output in a sea of verbose output
color_warning = colored.magenta  # for warnings about things likely to be problematic
