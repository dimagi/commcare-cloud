import jsonobject


class TerraformConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    aws_profile = jsonobject.StringProperty(required=True)
    account_alias = jsonobject.StringProperty()
    manage_users = jsonobject.BooleanProperty(default=True)
    state_bucket = jsonobject.StringProperty()
    state_bucket_region = jsonobject.StringProperty()
    region = jsonobject.StringProperty()
    environment = jsonobject.StringProperty()
    openvpn_image = jsonobject.StringProperty()
    azs = jsonobject.ListProperty(str)
    az_codes = jsonobject.ListProperty(str, default=['a', 'b', 'c'])
    vpc_begin_range = jsonobject.StringProperty()
    vpn_connections = jsonobject.ListProperty(lambda: VpnConnectionConfig)
    external_routes = jsonobject.ListProperty(lambda: ExternalRouteConfig)
    servers = jsonobject.ListProperty(lambda: ServerConfig)
    proxy_servers = jsonobject.ListProperty(lambda: ServerConfig)
    rds_instances = jsonobject.ListProperty(lambda: RdsInstanceConfig)
    redis = jsonobject.ObjectProperty(lambda: RedisConfig)

    @classmethod
    def wrap(cls, data):
        if 'aws_profile' not in data:
            data['aws_profile'] = data.get('account_alias')
        return super(TerraformConfig, cls).wrap(data)


class VpnConnectionConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    name = jsonobject.StringProperty()
    cidr_blocks = jsonobject.ListProperty(str)
    type = jsonobject.StringProperty()
    ip_address = jsonobject.StringProperty()
    bgp_asn = jsonobject.IntegerProperty()
    amazon_side_asn = jsonobject.IntegerProperty()


class ExternalRouteConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    cidr_block = jsonobject.StringProperty()
    gateway_id = jsonobject.StringProperty()


class ServerConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    server_name = jsonobject.StringProperty()
    server_instance_type = jsonobject.StringProperty()
    network_tier = jsonobject.StringProperty(choices=['app-private', 'public', 'db-private'])
    az = jsonobject.StringProperty()
    volume_size = jsonobject.IntegerProperty(default=20)
    block_device = jsonobject.ObjectProperty(lambda: BlockDevice, default=None)
    group = jsonobject.StringProperty()


class BlockDevice(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    volume_type = jsonobject.StringProperty(default='gp2', choices=['gp2', 'io1', 'standard'])
    volume_size = jsonobject.IntegerProperty(required=True)


class RdsInstanceConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    identifier = jsonobject.StringProperty(required=True)
    instance_type = jsonobject.StringProperty(required=True)  # should start with 'db.'
    multi_az = jsonobject.BooleanProperty(default=False)
    storage = jsonobject.IntegerProperty()
    create = jsonobject.BooleanProperty(default=True)
    username = "root"
    backup_window = "06:27-06:57"
    backup_retention = 30
    maintenance_window = "sat:08:27-sat:08:57"
    port = 5432
    params = jsonobject.DictProperty()


class RedisConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    create = jsonobject.BooleanProperty(default=True)
    node_type = jsonobject.StringProperty()
    num_cache_nodes = jsonobject.IntegerProperty(default=1)
    engine_version = jsonobject.StringProperty(default="4.0.10")
    parameter_group_name = jsonobject.StringProperty(default="default.redis4.0")
