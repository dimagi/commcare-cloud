import json
import os

import jsonobject

import yaml

from commcare_cloud.commands.command_base import CommandBase
from commcare_cloud.commands.utils import render_template
from commcare_cloud.environment.main import get_environment


class TerraformConfig(jsonobject.JsonObject):
    allow_dynamic_properties = False
    state_bucket = jsonobject.StringProperty()
    state_bucket_region = jsonobject.StringProperty()
    region = jsonobject.StringProperty()
    environment = jsonobject.StringProperty()
    azs = jsonobject.ListProperty(str)
    vpc_begin_range = jsonobject.StringProperty()
    external_routes = jsonobject.ListProperty(lambda: ExternalRouteConfig)
    servers = jsonobject.ListProperty(lambda: ServerConfig)
    proxy_servers = jsonobject.ListProperty(lambda: ServerConfig)
    rds_instances = jsonobject.ListProperty(lambda: RdsInstanceConfig)


class ExternalRouteConfig(jsonobject.JsonObject):
    allow_dynamic_properties = False
    cidr_block = jsonobject.StringProperty()
    gateway_id = jsonobject.StringProperty()


class ServerConfig(jsonobject.JsonObject):
    allow_dynamic_properties = False
    server_name = jsonobject.StringProperty()
    server_instance_type = jsonobject.StringProperty()
    network_tier = jsonobject.StringProperty(choices=['app-private', 'public', 'db-private'])
    az = jsonobject.StringProperty(choices=['a', 'b', 'c'])
    volume_size = jsonobject.IntegerProperty(default=20)


class RdsInstanceConfig(jsonobject.JsonObject):
    allow_dynamic_properties = False
    identifier = jsonobject.StringProperty()
    instance_type = jsonobject.StringProperty()  # should start with 'db.'
    storage = jsonobject.IntegerProperty()


def generate_terraform_entrypoint(config_yml):
    config = TerraformConfig.wrap(config_yml)
    return render_template('entrypoint.tf.j2', config.to_json(), os.path.dirname(__file__))


class MakeTerraformEntrypoint(CommandBase):
    command = "make-terraform-entrypoint"
    help = "Make terraform file to be run for this env"

    def run(self, args, unknown_args):
        environment = get_environment(args.env_name)
        with open(environment.paths.terraform_yml) as f:
            config_yml = yaml.load(f)
        config_yml['environment'] = config_yml.get('environment', environment)
        print(generate_terraform_entrypoint(config_yml))
