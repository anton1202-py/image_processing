import dataclasses as dc
import os

import yaml

from base_module.models import Model
from base_module.rabbit import RabbitFullConfig


@dc.dataclass
class PgConfig(Model):
    """."""

    host: str = dc.field(default=None)
    port: int = dc.field(default=None)
    user: str = dc.field(default=None)
    password: str = dc.field(default=None)
    database: str = dc.field(default=None)
    max_pool_connections: int = dc.field(default=100)
    debug: bool = dc.field(default=False)
    schema: str = dc.field(default="public")


@dc.dataclass
class ProjectConfig(Model):
    """."""

    pg: PgConfig = dc.field(default_factory=PgConfig)
    storage_dir: str = dc.field(default="/mnt")
    rabbit: RabbitFullConfig = dc.field(default=None)


config: ProjectConfig = ProjectConfig.load(
    yaml.safe_load(open(os.getenv("YAML_PATH", "config_files/config.yaml"))) or {}
)
