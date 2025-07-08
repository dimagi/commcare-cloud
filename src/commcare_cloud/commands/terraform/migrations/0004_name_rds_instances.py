def get_new_resource_address(environment, old_resource_address):
    import re
    server_matcher = re.compile(r'module\.postgresql-(\d+)\.(.*)$')

    match = server_matcher.match(old_resource_address)
    if match:
        index = int(match.group(1))
        rest = match.group(2)
        server_config = environment.terraform_config.rds_instances[index]
        return 'module.postgresql__{}.{}'.format(server_config.identifier, rest)
    else:
        return None
