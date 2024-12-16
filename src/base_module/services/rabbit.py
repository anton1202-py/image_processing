import datetime
import json
import time
import typing as t
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum
from uuid import UUID

import pika
from pika import BlockingConnection, ConnectionParameters, PlainCredentials, spec
from pika.adapters.blocking_connection import BlockingChannel

from base_module.exceptions import ModuleException
from base_module.logger import ClassesLoggerAdapter
from base_module.models import Model
from base_module.rabbit import (
    JsonMessageModel,
    MessageModel,
    RabbitConsumerConfig,
    RabbitFullConfig,
    RabbitPublisherConfig,
)


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, MessageModel):
            return {
                "payload": obj.payload,
                "trace_id": obj.trace_id,
                "ttl": obj.ttl,
            }
        return super().default(obj)


class FormatDumps(json.JSONEncoder):
    """."""

    def default(self, o):
        if isinstance(o, (datetime.date, datetime.datetime)):
            return o.isoformat()
        if isinstance(o, UUID):
            return o.hex
        if isinstance(o, Model):
            return o.dump()
        if isinstance(o, Enum):
            return o.value

        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            return str(o)


class RabbitService:
    """."""

    @property
    def _can_consume(self):
        return isinstance(self._config, RabbitConsumerConfig)

    @property
    def _can_publish(self):
        return isinstance(self._config, RabbitPublisherConfig)

    @property
    def config(self):
        return deepcopy(self._config)

    def __init__(
        self,
        config: t.Union[
            RabbitFullConfig, t.Union[RabbitConsumerConfig, RabbitPublisherConfig]
        ],
    ):
        """."""
        self._config = config
        self._logger = ClassesLoggerAdapter.create(self)

    @contextmanager
    def _queue_connection(self):
        connection = BlockingConnection(
            ConnectionParameters(
                host=self._config.host,
                port=self._config.port,
                credentials=PlainCredentials(
                    username=self._config.user, password=self._config.password
                ),
                heartbeat=0,
            )
        )
        channel = connection.channel()
        yield channel
        channel.close()
        connection.close()

    def declare_dlx(
        self,
        routing_key: str,
        dlx_queue_name: str,
        message_ttl: int,
        dlx_exchange: str = "",
        max_priority: int = 5,
    ):
        with self._queue_connection() as channel:
            channel.queue_declare(
                queue=dlx_queue_name,
                passive=False,
                durable=True,
                arguments={
                    "x-message-ttl": message_ttl * 1000,
                    "x-dead-letter-exchange": dlx_exchange,
                    "x-dead-letter-routing-key": routing_key,
                    "x-max-priority": max_priority,
                },
            )

    def _make_properties(
        self, properties: pika.BasicProperties
    ) -> pika.BasicProperties:
        properties = properties or pika.BasicProperties()
        properties.delivery_mode = spec.PERSISTENT_DELIVERY_MODE
        if not properties.reply_to and self._config.reply_to:
            properties.reply_to = self._config.reply_to

        return properties

    def publish(
        self,
        message: MessageModel,
        properties: pika.BasicProperties = None,
        publish_to: str = None,
        exchange: str = None,
    ) -> bool:
        if not self._can_publish:
            raise ModuleException(
                ("Конфиг не соответствует конфигу отправки").encode("utf-8")
            )

        publish_to = publish_to or self._config.routing_key
        exchange = exchange or self._config.exchange
        properties = self._make_properties(properties)

        try:
            with self._queue_connection() as channel:
                channel.basic_publish(
                    exchange=exchange,
                    routing_key=publish_to,
                    body=json.dumps(message, cls=FormatDumps).encode(),
                    properties=properties,
                )
                self._logger.info("Отправлено сообщение", extra={"queue": publish_to})
                return True
        except Exception as e:
            self._logger.error(
                "Ошибка отправки сообщения",
                extra={
                    "message": message,
                    "exchange": exchange,
                    "publish_to": publish_to,
                    "properties": properties,
                    "e": e,
                },
                exc_info=True,
            )
            return False

    def publish_many(
        self,
        messages: t.List[MessageModel],
        properties: pika.BasicProperties = None,
        publish_to: str = None,
        exchange: str = None,
    ):
        if not self._can_publish:
            raise ModuleException(
                ("Конфиг не соответствует конфигу отправки").encode("utf-8")
            )

        publish_to = publish_to or self._config.routing_key
        exchange = exchange or self._config.exchange
        properties = self._make_properties(properties)

        try:
            with self._queue_connection() as channel:
                for message in messages:
                    self._logger.info(
                        "Отправлено сообщение", extra={"queue": publish_to}
                    )
                    channel.basic_publish(
                        exchange=exchange,
                        routing_key=publish_to,
                        body=json.dumps(message, cls=FormatDumps).encode(),
                        properties=properties,
                    )
                return True
        except Exception as e:
            self._logger.error(
                "Ошибка отправки сообщений",
                extra={
                    "messages": messages,
                    "exchange": exchange,
                    "publish_to": publish_to,
                    "properties": properties,
                    "e": e,
                },
                exc_info=True,
            )
            return False

    def _receiver_proxy(self, receiver, message_type: t.Type[MessageModel]):
        def _handle_message(
            ch: BlockingChannel,
            method: spec.Basic.Deliver,
            properties: pika.BasicProperties,
            body: bytes,
        ):
            nonlocal self
            try:
                message = message_type.load(json.loads(body.decode()))
            except Exception as e:
                self._logger.warn(
                    "Сообщение не подходит под формат", extra={"body": body, "e": e}
                )
                ch.basic_ack(method.delivery_tag)
                return

            try:
                message_handled = receiver(
                    message=message, channel=ch, method=method, properties=properties
                )
                not message_handled and ch.basic_ack(method.delivery_tag)
            except Exception as e:
                self._logger.error(
                    "Ошибка обработки сообщения",
                    exc_info=True,
                    extra={"body": body, "e": e},
                )
                ch.basic_nack(method.delivery_tag)

        return _handle_message

    def run_consume(
        self, receiver, message_type: t.Type[MessageModel] = JsonMessageModel
    ):
        if not self._can_consume:
            raise ModuleException(
                ("Конфиг не соответствует конфигу прослушивания").encode("utf-8")
            )

        while True:
            try:
                self._logger.info(
                    "Запуск прослушивания очереди",
                    extra={"queue": self._config.queue_name},
                )
                with self._queue_connection() as channel:
                    channel.basic_qos(prefetch_count=1)
                    channel.queue_declare(
                        queue=self._config.queue_name,
                        durable=True,
                        arguments={"x-max-priority": self._config.max_priority},
                    )
                    channel.basic_consume(
                        queue=self._config.queue_name,
                        auto_ack=False,
                        exclusive=False,
                        on_message_callback=self._receiver_proxy(
                            receiver, message_type
                        ),
                    )
                    channel.start_consuming()

            except Exception as e:
                self._logger.error(
                    "Ошибка подключения или прослушивания очереди",
                    extra={"queue": self._config.queue_name, "e": e},
                    exc_info=True,
                )

            time.sleep(self._config.error_timeout)
