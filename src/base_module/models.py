import dataclasses as dc
import typing as t
from datetime import date, datetime
from enum import Enum

import dataclass_factory
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from base_module.exceptions import ModuleException

TV_MODEL = t.TypeVar("TV_MODEL")

Base = declarative_base()


def default_loader(value, cls, loader):
    if not isinstance(value, cls):
        return loader(value)
    return value


def iso_loader(value: str, cls):
    if isinstance(value, cls):
        return value
    if value.endswith("Z"):
        return cls.fromisoformat(value.replace("Z", ""))
    return cls.fromisoformat(value)


@dc.dataclass
class Model:
    """."""

    SCHEMAS: t.ClassVar = {
        datetime: dataclass_factory.Schema[datetime](
            parser=lambda _: iso_loader(_, datetime), serializer=datetime.isoformat
        ),
        date: dataclass_factory.Schema(
            parser=lambda _: default_loader(_, date, date.fromisoformat),
            serializer=date.isoformat,
        ),
    }
    FACTORY: t.ClassVar = dataclass_factory.Factory(schemas=SCHEMAS)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.FACTORY = dataclass_factory.Factory(schemas=cls.SCHEMAS)

    def __post_init__(self):
        pass

    @classmethod
    def __improve_schemas(cls):
        for key, schema in cls.SCHEMAS.items():
            cls.FACTORY.schemas.setdefault(key, schema)

    @classmethod
    def load(cls: t.Type[TV_MODEL], data: dict) -> TV_MODEL:
        cls.__improve_schemas()
        if isinstance(data, cls):
            return data
        return cls.FACTORY.load(data, cls)

    def validate(self):
        self.__post_init__()

    def update(self, data: dict):
        [setattr(self, f, v) for f, v in data.items()]

    def dump(self) -> dict:
        self.__improve_schemas()
        return self.FACTORY.dump(self)

    def reload(self) -> TV_MODEL:
        return self.load(self.dump())


def view(cls):
    names = []
    for f in getattr(cls, "__fields__", []):
        if isinstance(f, dc.Field):
            names.append(f.name)
        if isinstance(f, str):
            names.append(f)
        else:
            names.append(getattr(f, "key", None))

    def _view_dump(model):
        if isinstance(model, Model):
            dumped: dict = model.dump()
        else:
            dumped = model

        result = {}
        for key in names:
            if key in dumped:
                result[key] = dumped[key]
            else:
                result[key] = getattr(model, key)

        return result

    return lambda _: _view_dump(_)


class BaseOrmModel(Model):
    """."""

    __sa_dataclass_metadata_key__: t.ClassVar = "sa"
    __tablename__: t.ClassVar = None
    REGISTRY: t.ClassVar = orm.registry()


class ModelException(ModuleException):
    """."""

    prefix = "ошибка обработки модели"


class ValuedEnum(Enum):
    """."""

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def values(cls):
        return cls._value2member_map_.keys()

    @classmethod
    def elements(cls):
        return cls._value2member_map_.values()

    @classmethod
    def from_key(cls, key, safe: bool = True):
        for value in cls._value2member_map_.values():
            if str(value) == f"{cls.__name__}.{key}":
                return value

        if not safe:
            raise ModelException(
                (f"Недопустимое значение: {key}").encode("utf-8"), code=400
            )

    @classmethod
    def from_value(cls, value, safe: bool = True):
        if isinstance(value, cls):
            return value
        for num in cls._value2member_map_.values():
            if num.value == value:
                return num

        if value is not None and not safe:
            raise ModelException(
                (f"Недопустимое значение: {value}").encode("utf-8"), code=400
            )

    @classmethod
    def from_name(cls, name: str):
        return cls._member_map_[name]

    @classmethod
    def to_dict(cls):
        res = {}
        for key, item_value in cls._member_map_.items():
            res[key] = item_value.value
        return res
