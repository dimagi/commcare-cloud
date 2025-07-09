from unittest.mock import patch

from commcare_cloud.user_utils import StringIsGuess


def setup_package():
    global patches
    patches = [
        patch.dict("os.environ", COMMCARE_CLOUD_DEFAULT_USERNAME=""),
        # handle memoized decorator (in case get_default_username has already been called)
        patch(
            "commcare_cloud.user_utils.get_default_username",
            lambda: StringIsGuess("", is_guess=True),
        ),

    ]
    for patch_ in patches:
        patch_.start()


def teardown_package():
    for patch_ in patches:
        patch_.stop()


def _install_nose_plugins():
    # HACK Plugins cannot be configured the normal way (in setup.py
    # entry_points) because they cannot be imported at plugin
    # configuration time without making them part of non-test code.
    #
    # This will not work for all plugins since the plugin lifecycle
    # has already begun by the time this is called.
    #
    # `nosetests -p` emits a warning with entry_points config:
    # RuntimeWarning: Unable to load plugin
    # classcleanup = tests.classcleanup:ClassCleanupPlugin:
    # No module named 'tests.classcleanup'
    def get_plugin_manager():
        frame = sys._getframe()
        while not hasattr(frame.f_locals.get("self"), "config"):
            frame = frame.f_back
        return frame.f_locals["self"].config.plugins

    import sys
    from .classcleanup import ClassCleanupPlugin
    get_plugin_manager().addPlugin(ClassCleanupPlugin())


_install_nose_plugins()
