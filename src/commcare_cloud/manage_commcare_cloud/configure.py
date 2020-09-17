from __future__ import absolute_import
from __future__ import print_function
import os
import textwrap
from six.moves import shlex_quote

from clint.textui import puts

from commcare_cloud.cli_utils import ask
from commcare_cloud.colors import color_summary, color_notice, color_code
from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.environment.paths import DIMAGI_ENVIRONMENTS_DIR, get_virtualenv_bin_path, \
    PACKAGE_BASE


class Configure(CommandBase):
    command = 'configure'
    help = 'Guide to setting up everything you need to work with commcare-cloud'

    def make_parser(self):
        self.parser.add_argument('--environments-dir')
        self.parser.add_argument('--quiet', action='store_true')

    @staticmethod
    def _determine_environments_dir(quiet):
        environments_dir = None

        environ_value = os.environ.get('COMMCARE_CLOUD_ENVIRONMENTS')

        if quiet:
            return environ_value or DIMAGI_ENVIRONMENTS_DIR

        def have_same_realpath(dir1, dir2):
            return os.path.realpath(dir1) == os.path.realpath(dir2)

        if not environments_dir:
            if os.path.exists(DIMAGI_ENVIRONMENTS_DIR):
                if ask("Do you work or contract for Dimagi?"):
                    print("OK, we'll give you Dimagi's default environments (production, staging, etc.).")
                    environments_dir = DIMAGI_ENVIRONMENTS_DIR

        if not environments_dir:
            if environ_value and not have_same_realpath(environ_value, DIMAGI_ENVIRONMENTS_DIR):
                print("I see you have COMMCARE_CLOUD_ENVIRONMENTS set to {} in your environment".format(environ_value))
                if ask("Would you like to use environments at that location?"):
                    environments_dir = environ_value

        if not environments_dir:
            default_environments_dir = "~/.commcare-cloud/environments"
            environments_dir = os.path.expanduser(default_environments_dir)
            print("To use commcare-cloud, you have to have an environments directory. "
                  "This is where you will store information about your cluster setup, "
                  "such as the IP addresses of the hosts in your cluster, "
                  "how different services are distributed across the machines, "
                  "and all settings specific to your CommCare instance.")
            if ask("Would you like me to create an empty one for you at "
                   "{}?".format(default_environments_dir)):
                for dir_name in ['_authorized_keys', '_users']:
                    dir_path = os.path.expanduser(os.path.join(default_environments_dir, dir_name))
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                print("Okay, I've got the env started for you, "
                      "but you're going to have to fill out the rest before you can do much. "
                      "For more information, see https://dimagi.github.io/commcare-cloud/commcare-cloud/env/ "
                      "and refer to the examples at "
                      "https://github.com/dimagi/commcare-cloud/tree/master/environments.")

        return environments_dir

    def _write_load_config_sh(self, environments_dir, quiet):
        puts(color_summary("Let's get you set up to run commcare-cloud."))

        if not environments_dir:
            environments_dir = self._determine_environments_dir(quiet=quiet)

        commcare_cloud_dir = os.path.expanduser("~/.commcare-cloud")
        if not os.path.exists(commcare_cloud_dir):
            os.makedirs(commcare_cloud_dir)
        load_config_file = os.path.expanduser("~/.commcare-cloud/load_config.sh")
        if not os.path.exists(load_config_file) or \
                ask("Overwrite your ~/.commcare-cloud/load_config.sh?", quiet=quiet):
            with open(load_config_file, 'w') as f:
                f.write(textwrap.dedent("""
                    # auto-generated with `manage-commcare-cloud configure`:
                    export COMMCARE_CLOUD_ENVIRONMENTS={COMMCARE_CLOUD_ENVIRONMENTS}
                    export PATH=$PATH:{virtualenv_path}
                    source {PACKAGE_BASE}/.bash_completion
                """.format(
                    COMMCARE_CLOUD_ENVIRONMENTS=shlex_quote(environments_dir),
                    virtualenv_path=get_virtualenv_bin_path(),
                    PACKAGE_BASE=PACKAGE_BASE,
                )).strip())
        puts(color_notice("Add the following to your ~/.bash_profile:"))
        puts(color_code("source ~/.commcare-cloud/load_config.sh"))
        puts(color_notice(
            "and then open a new shell. "
            "You should be able to run `commcare-cloud` without entering your virtualenv."))

    def run(self, args, unknown_args):
        self._write_load_config_sh(environments_dir=args.environments_dir, quiet=args.quiet)
