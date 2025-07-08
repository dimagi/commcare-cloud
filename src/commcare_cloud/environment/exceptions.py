class EnvironmentException(Exception):
    """
    Used for any environment, configuration, general setup issues encountered
    """
    pass


class PGConfigException(EnvironmentException):
    pass
