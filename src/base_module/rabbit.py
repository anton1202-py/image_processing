import dataclasses as dc
import typing
import typing as t

from base_module.logger import ClassesLoggerAdapter
from base_module.models import TV_MODEL, Model


@dc.dataclass
class _CredentialsConfig(Model):
    """."""

    host: str = dc.field(default="rabbit")
    port: int = dc.field(default=5672)
    user: str = dc.field(default="admin")
    password: str = dc.field(default="12345")


@dc.dataclass
class RabbitPublisherConfig(_CredentialsConfig):
    """."""

    exchange: str = dc.field(default="")
    routing_key: str = dc.field(default="")
    reply_to: str = dc.field(default=None)


@dc.dataclass
class RabbitConsumerConfig(_CredentialsConfig):
    """."""

    queue_name: str = dc.field(default="")
    error_timeout: int = dc.field(default=10)
    max_priority: int = dc.field(default=5)


@dc.dataclass
class RabbitFullConfig(RabbitConsumerConfig, RabbitPublisherConfig):
    """."""


TV_PAYLOAD = t.TypeVar("TV_PAYLOAD")


@dc.dataclass
class MessageModel(Model, t.Generic[TV_PAYLOAD]):
    """."""

    T: t.ClassVar

    payload: TV_PAYLOAD = dc.field()
    trace_id: str = dc.field(default=ClassesLoggerAdapter.DEFAULT_TRACE_ID)
    ttl: typing.Optional[int] = dc.field(default=0)

    @classmethod
    def load(cls: t.Type[TV_MODEL], data: dict) -> TV_MODEL:
        data.setdefault("trace_id", ClassesLoggerAdapter.DEFAULT_TRACE_ID)
        ClassesLoggerAdapter.TRACE_ID.set(data["trace_id"])
        return super(MessageModel, cls).load(data)

    @classmethod
    def lazy_load(cls, payload: TV_PAYLOAD, **kwargs):
        return cls(
            payload=payload, trace_id=ClassesLoggerAdapter.TRACE_ID.get(), **kwargs
        )


@dc.dataclass
class _TaskIdentModel(Model):
    """."""

    task_id: int = dc.field()


@dc.dataclass
class TaskIdentMessageModel(MessageModel[_TaskIdentModel]):
    """."""

    T = _TaskIdentModel


@dc.dataclass
class JsonMessageModel(MessageModel[dict]):
    """."""

    T = dict
