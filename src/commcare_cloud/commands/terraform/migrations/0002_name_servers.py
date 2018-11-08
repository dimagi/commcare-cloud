def get_new_resource_address(environment, old_resource_address):
    import re
    server_matcher = re.compile(r'^module.servers.aws_instance.server\[(\d+)\]$')

    match = server_matcher.match(old_resource_address)
    if match:
        index = int(match.group(1) or 0)
        server_config = environment.terraform_config.servers[index]
        return 'module.server__{}.aws_instance.server'.format(server_config.server_name)
    elif old_resource_address == 'module.proxy_servers.aws_instance.server':
        server_config = environment.terraform_config.proxy_servers[0]
        return 'module.proxy_server__{}.aws_instance.server'.format(server_config.server_name)
    elif old_resource_address == 'aws_eip.proxy':
        server_config = environment.terraform_config.proxy_servers[0]
        return 'aws_eip.{}-production'.format(server_config.server_name)
    else:
        return None
