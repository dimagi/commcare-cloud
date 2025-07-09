def get_new_resource_address(environment, old_resource_address):
    import re
    server_matcher = re.compile(r'^module\.proxy_server__([\w-]+)\.aws_instance\.server$')
    match = server_matcher.match(old_resource_address)
    if match:
        return 'module.server__{}.aws_instance.server'.format(match.group(1))
    else:
        return None
