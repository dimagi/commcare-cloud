def get_new_resource_address(environment, old_resource_address):
    prefix = 'module.commcarehq.'
    if old_resource_address.startswith(prefix):
        return old_resource_address[len(prefix):]
