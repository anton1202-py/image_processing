import dataclasses as dc
import typing
from datetime import datetime

import sqlalchemy as sa

from base_module.models import BaseOrmModel, ValuedEnum


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

BaseOrmModel.REGISTRY.mapped(FileInfo)


class TaskStatus(ValuedEnum):
    """."""

    NEW = "new"
    PROCESSING = "processing"
    ERROR = "error"
    DONE = "done"


@dc.dataclass
class ImageProcessingTask(BaseOrmModel):
    """."""

    __tablename__ = "Image_processing_task"

    task_id: typing.Optional[int] = dc.field(
        default=None, metadata={"sa": sa.Column(sa.Integer, primary_key=True)}
    )
    file_id: int = dc.field(default=None, metadata={"sa": sa.Column(sa.Integer)})
    processed_file_id: int = dc.field(default=0, metadata={"sa": sa.Column(sa.Integer)})
    status: TaskStatus = dc.field(
        default=TaskStatus.NEW,
        metadata={"sa": sa.Column(sa.Enum(TaskStatus, name="Image_processing_status"))},
    )
    processing_parameters: dict = dc.field(
        default=None, metadata={"sa": sa.Column(sa.JSON)}
    )
    created_at: typing.Optional[datetime] = dc.field(
        default_factory=datetime.now, metadata={"sa": sa.Column(sa.DateTime)}
    )
    updated_at: typing.Optional[datetime] = dc.field(
        default=None, metadata={"sa": sa.Column(sa.DateTime)}
    )


BaseOrmModel.REGISTRY.mapped(ImageProcessingTask)