import contextvars
import logging
import typing as t


class ClassesLoggerAdapter(logging.LoggerAdapter):
    """."""

    APP_EXTRA = {}
    DEFAULT_TRACE_ID = "root"
    TRACE_ID = contextvars.ContextVar("trace_id", default=DEFAULT_TRACE_ID)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.service_name = cls.__name__

    def __init__(self, **kwargs):
        """."""
        super().__init__(logging.getLogger(), kwargs.pop("extra", {}))

    @classmethod
    def create(cls, issuer: t.Union[str, t.Type, object], **kwargs):
        logger = cls(**kwargs)
        logger.service_name = (
            issuer if isinstance(issuer, str) else type(issuer).__name__
        )
        return logger

    def process(self, msg, kwargs):
        kwargs["extra"] = {
            "data": kwargs.get("extra") or {},
            "declarer": self.service_name,
            "trace_id": self.TRACE_ID.get(),
            **self.extra,
            **self.APP_EXTRA,
        }
        return msg, kwargs
