import sqlalchemy as sa
import sqlalchemy.orm


def get_key(attr) -> str:
    return attr.key


def get_field(type_model, field) -> sqlalchemy.orm.InstrumentedAttribute:
    return getattr(type_model, str(field), None)


def col2field(col) -> sqlalchemy.orm.InstrumentedAttribute:
    return col


def in_(attr, value):
    return attr.in_(value)


def has(attr, value):
    return attr.has(value)


def any_(attr, value):
    return attr.any(value)


def eq(field, value):
    return field == value


def neq(field, value):
    return field != value


def like(field, value):
    return field.like(f"%{value}%")


def not_like(field, value):
    return field.not_like(f"%{value}%")


def ilike(field, value):
    return field.ilike(f"%{value}%")


def not_ilike(field, value):
    return field.not_ilike(f"%{value}%")


def not_in(attr, value):
    return ~in_(attr, value)
