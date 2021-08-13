from __future__ import absolute_import
from __future__ import unicode_literals

import re

import jsonobject
from clint.textui import puts
from commcare_cloud.colors import color_warning
from six.moves import range


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
    openvpn_instance_type = jsonobject.StringProperty()
    openvpn_az = jsonobject.StringProperty()
    azs = jsonobject.ListProperty(str)
    az_codes = jsonobject.ListProperty(str, default=['a', 'b', 'c'])
    ssl_policy = jsonobject.StringProperty(default="ELBSecurityPolicy-2016-08")
    vpc_begin_range = jsonobject.StringProperty()
    vpn_connections = jsonobject.ListProperty(lambda: VpnConnectionConfig)
    external_routes = jsonobject.ListProperty(lambda: ExternalRouteConfig)
    servers = jsonobject.ListProperty(lambda: ServerConfig)
    proxy_servers = jsonobject.ListProperty(lambda: ServerConfig)
    rds_instances = jsonobject.ListProperty(lambda: RdsInstanceConfig)
    pgbouncer_nlbs = jsonobject.ListProperty(lambda: PgbouncerNlbs)
    internal_albs = jsonobject.ListProperty(lambda: InternalAlbs)
    elasticache = jsonobject.ObjectProperty(lambda: ElasticacheConfig, default=None)
    elasticache_cluster = jsonobject.ObjectProperty(lambda: ElasticacheClusterConfig, default=None)
    r53_private_zone = jsonobject.ObjectProperty(lambda: RoutePrivateZoneConfig, default=None)
    efs_file_systems = jsonobject.ListProperty(lambda: EfsFileSystem, default=None)
    ec2_auto_recovery = jsonobject.ListProperty(lambda: Ec2AutoRecovery, default=None)

    @classmethod
    def wrap(cls, data):
        if 'aws_profile' not in data:
            data['aws_profile'] = data.get('account_alias')
        return super(TerraformConfig, cls).wrap(data)

    def to_generated_json(self):
        obj = self.to_json()
        obj['servers'] = [server.to_generated_json() for server in self.servers]
        obj['proxy_servers'] = [server.to_generated_json() for server in self.proxy_servers]
        return obj


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
    volume_type = jsonobject.StringProperty(default='gp3')
    volume_encrypted = jsonobject.BooleanProperty(default=True, required=True)
    block_device = jsonobject.ObjectProperty(lambda: BlockDevice, default=None)
    group = jsonobject.StringProperty()
    os = jsonobject.StringProperty(required=True, choices=['trusty', 'bionic', 'ubuntu_pro_bionic'])
    server_auto_recovery = jsonobject.BooleanProperty(default=False)
    count = jsonobject.IntegerProperty(default=None)

    @classmethod
    def wrap(cls, data):
        self = super(cls, ServerConfig).wrap(data)
        if self.count is not None and not self.server_name.split('-', 1)[0].endswith('{i}'):
            raise ValueError('To use count, server_name must be a template string using {i}, '
                             'and {i} must be the final part before the env suffix')
        return self

    def get_all_server_names(self):
        if self.count is None:
            # e.g. server0-test => ["server0-test"]
            return [self.server_name]
        else:
            # e.g. server_a{i}-test => ["server_a000-test", "server_a001-test", ...]
            return [self.server_name.format(i='{:03d}'.format(i)) for i in range(self.count)]

    def get_all_host_names(self):
        host_name = self.server_name.split('-', 1)[0]
        if self.count is None:
            # e.g. server0-test => ["server0"]
            return [host_name]
        else:
            # e.g. server_a{i}-test => ["server_a000", "server_a001", ...]
            return [host_name.format(i='{:03d}'.format(i)) for i in range(self.count)]

    def get_host_group_name(self):
        if self.count is None:
            raise ValueError("Can only call get_host_group_name() on a server with count")
        else:
            # e.g. server_a{i}-test => ["server_a"]
            return self.server_name.split('-', 1)[0][:-3]

    def to_generated_json(self):
        obj = self.to_json()
        obj['get_all_server_names'] = self.get_all_server_names()
        return obj


class BlockDevice(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    volume_type = jsonobject.StringProperty(default='gp3', choices=['gp2', 'gp3', 'io1', 'standard'])
    volume_size = jsonobject.IntegerProperty(required=True)
    encrypted = jsonobject.BooleanProperty(default=True, required=True)


class RdsInstanceConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    identifier = jsonobject.StringProperty(required=True)
    engine_version = jsonobject.StringProperty(default='9.6.6')
    instance_type = jsonobject.StringProperty(required=True)  # should start with 'db.'
    multi_az = jsonobject.BooleanProperty(default=False)
    storage = jsonobject.IntegerProperty(required=True)
    max_storage = jsonobject.IntegerProperty(default=0)
    create = jsonobject.BooleanProperty(default=True)
    username = "root"
    backup_window = jsonobject.StringProperty(default="06:27-06:57")
    backup_retention = jsonobject.IntegerProperty(default=30)
    monitoring_interval = jsonobject.IntegerProperty(default=60)
    maintenance_window = "sat:08:27-sat:08:57"
    port = 5432
    params = jsonobject.DictProperty()

    _default_params = {
        'pg_stat_statements.track': 'all',
        'pg_stat_statements.max': 10000,
        'track_activity_query_size': 2048,
    }

    @classmethod
    def wrap(cls, data):
        if 'params' not in data:
            data['params'] = {}
        params = data['params']
        for name, value in cls._default_params.items():
            if name not in params:
                params[name] = value
        return super(RdsInstanceConfig, cls).wrap(data)


class PgbouncerNlbs(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    name = jsonobject.StringProperty(required=True)
    identifier = jsonobject.StringProperty(required=False)
    targets = jsonobject.ListProperty(str)

    @classmethod
    def wrap(cls, data):
        self = super(PgbouncerNlbs, cls).wrap(data)
        if not self.identifier:
            self.identifier = self.name.replace('_', '-')
        if not re.match('[a-z]+-nlb-[a-z]+', self.identifier):
            raise ValueError("commcare-cloud requires pgbouncer nlb identifier to be of the form 'pg{name}-nlb-{environment}'")
        return self

class InternalAlbs(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    name = jsonobject.StringProperty(required=True)
    identifier = jsonobject.StringProperty(required=False)
    targets = jsonobject.ListProperty(str)
    target_port = jsonobject.IntegerProperty(required=True)
    listener_port = jsonobject.IntegerProperty(required=True)
    health_check_interval = jsonobject.IntegerProperty(default=30)
    @classmethod
    def wrap(cls, data):
        self = super(InternalAlbs, cls).wrap(data)
        if not self.identifier:
            self.identifier = self.name.replace('_', '-')
        if not re.match('[a-z]+-alb-[a-z]+', self.identifier):
            raise ValueError("commcare-cloud requires internal alb identifier to be of the form 'internal{name}-alb-{environment}'")
        return self

class ElasticacheConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    create = jsonobject.BooleanProperty(default=True)
    node_type = jsonobject.StringProperty()
    num_cache_nodes = jsonobject.IntegerProperty(default=1)
    engine_version = jsonobject.StringProperty(default="4.0.10")
    parameter_group_name = jsonobject.StringProperty(default="default.redis4.0")

class ElasticacheClusterConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    create = jsonobject.BooleanProperty(default=True)
    cache_node_type = jsonobject.StringProperty(default="cache.t3.micro")
    cache_engine = jsonobject.StringProperty(default="redis")
    cache_engine_version = jsonobject.StringProperty(default="4.0.10")
    cache_prameter_group = jsonobject.StringProperty(default="default.redis4.0")
    automatic_failover = jsonobject.BooleanProperty(default=True)
    transit_encryption = jsonobject.BooleanProperty(default=False)
    at_rest_encryption = jsonobject.BooleanProperty(default=True)
    multi_az = jsonobject.BooleanProperty(default=True)
    auto_minor_version = jsonobject.BooleanProperty(default=False)
    cluster_size = jsonobject.IntegerProperty(default=1)
    maintenance_window = jsonobject.StringProperty(default="sun:03:30-sun:04:30")
    snapshot_retention = jsonobject.IntegerProperty(default=5)
    snapshot_window = jsonobject.StringProperty(default="07:30-08:30")

class RoutePrivateZoneConfig(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    create = jsonobject.BooleanProperty(default=True)
    domain_name = jsonobject.StringProperty()
    create_record = jsonobject.BooleanProperty(default=True)
    route_names = jsonobject.StringProperty()

class EfsFileSystem(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    create = jsonobject.BooleanProperty(default=True)
    transition_to_ia = jsonobject.StringProperty(required=True)
    efs_name = jsonobject.StringProperty(required=True)
    create_access = jsonobject.BooleanProperty(default=True)
    create_mount = jsonobject.BooleanProperty(default=True)
    create_record = jsonobject.BooleanProperty(default=True)
    domain_name = jsonobject.StringProperty(required=True)
    record_type = jsonobject.StringProperty(default="CNAME")
    route_names = jsonobject.StringProperty(required=True)

class Ec2AutoRecovery(jsonobject.JsonObject):
    _allow_dynamic_properties = False
    targets = jsonobject.ListProperty(str)
    name_prefix = jsonobject.StringProperty(required=True)
        