import dataclasses as dc
import typing
from datetime import datetime

import sqlalchemy as sa

from base_module.models import BaseOrmModel, ValuedEnum


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