def get_new_resource_address(old_resource_address):
    """
    Specify migration by specifying for a given old address what the new address should be

    All addresses will be / should be given in the format used in `terraform state list`.

    The migration is then essentially (in peudocode):

    for resource in `terraform state list`:
        `terraform state mv ${resource} ${get_new_resource_address(resource)}`
    """
