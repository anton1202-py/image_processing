import dataclasses as dc
import typing
from datetime import datetime

import sqlalchemy as sa

from base_module.models import BaseOrmModel


@dc.dataclass
class FileInfo(BaseOrmModel):
    """."""

    __tablename__ = "file_info"
    id: typing.Optional[int] = dc.field(
        default=None, metadata={"sa": sa.Column(sa.Integer, primary_key=True)}
    )
    name: str = dc.field(
        default=None, metadata={"sa": sa.Column(sa.String, nullable=False)}
    )
    extension: str = dc.field(default=None, metadata={"sa": sa.Column(sa.String)})
    path_file: str = dc.field(default=None, metadata={"sa": sa.Column(sa.String)})
    size: float = dc.field(default=None, metadata={"sa": sa.Column(sa.Float)})
    date_create: datetime = dc.field(
        default_factory=datetime.utcnow,
        metadata={"sa": sa.Column(sa.DateTime, default=sa.func.now())},
    )
    date_change: typing.Optional[datetime] = dc.field(
        default=None, metadata={"sa": sa.Column(sa.DateTime)}
    )
    comment: str = dc.field(default=None, metadata={"sa": sa.Column(sa.Text)})


BaseOrmModel.REGISTRY.mapped(FileInfo)
