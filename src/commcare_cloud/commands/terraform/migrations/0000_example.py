def get_new_resource_address(environment, old_resource_address):
    """
    Specify migration by specifying for a given old address what the new address should be

    A falsy value is interpreted as skip / no change.
    All addresses will be / should be given in the format used in `terraform state list`.

    The migration is then essentially (in pseudocode, and with better edge-case management):

    for resource in `terraform state list`:
        if get_new_resource_address(environment, resource):
            `terraform state mv ${resource} ${get_new_resource_address(environment, resource)}`
    """
