import logging
import time
import typing as t

import flask
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_utils import create_database, database_exists

from base_module.exceptions import ModuleException
from base_module.logger import ClassesLoggerAdapter
from base_module.models import BaseOrmModel
from base_module.singletons import ThreadIsolatedSingleton
from config import PgConfig


class ConnectionsException(ModuleException):
    """."""

    @classmethod
    def acquire_error(cls):
        try:
            raise cls(("Сервис временно недоступен").encode("utf-8"), code=503)
        except Exception as e:
            logging.error(str(e).encode("utf-8"))


class PgConnectionInj(metaclass=ThreadIsolatedSingleton):
    """."""

    def __init__(
        self,
        conf: PgConfig,
        init_error_timeout: int = 5,
        acquire_attempts: int = 5,
        acquire_error_timeout: int = 5,
        init_statements: list = None,
    ):
        """."""
        self._conf = conf
        self._init_error_timeout = init_error_timeout
        self._acquire_attempts = acquire_attempts
        self._acquire_error_timeout = acquire_error_timeout
        self._init_statements = init_statements or list()
        self._pg: t.Union[sa.orm.scoped_session, Session, None] = None
        self._logger = ClassesLoggerAdapter.create(self)

    def _acquire_session(self) -> Session:
        if not self._pg:
            self._init_db()
        if not self._pg.is_active:
            with self._pg.begin():
                self._pg.execute(sa.text(f"SET ROLE {self._conf.user}"))
        return self._pg

    def acquire_session(self) -> Session:
        for i in range(self._acquire_attempts):
            try:
                return self._acquire_session()
            except Exception as e:
                time.sleep(self._acquire_error_timeout)

        return ConnectionsException.acquire_error()

    def __set_schemas(self):
        BaseOrmModel.REGISTRY.metadata.schema = self._conf.schema
        schemas = [self._conf.schema]
        for table in BaseOrmModel.REGISTRY.metadata.sorted_tables:
            table: sa.schema.Table
            if table.schema and table.schema not in schemas:
                schemas.append(table.schema)

            if not table.schema:
                table.schema = self._conf.schema

            for col in list(table.columns):  # noqa
                if isinstance(col.type, sa.sql.sqltypes.Enum):
                    col.type.schema = col.type.schema or self._conf.schema
                    if col.type.schema not in schemas:
                        schemas.append(col.type.schema)
        return schemas

    def _init_db(self):
        engine = sa.create_engine(
            sa.engine.URL.create(
                "postgresql+psycopg2",
                self._conf.user,
                self._conf.password,
                self._conf.host,
                self._conf.port,
                self._conf.database,
            ),
            echo=self._conf.debug,
            query_cache_size=0,
        )
        if not database_exists(engine.url):
            create_database(engine.url)
        schemas = self.__set_schemas()

        with engine.connect() as connection:
            connection: sa.engine.base.Connection
            with connection.begin():
                dialect = connection.dialect
                for schema in schemas:
                    if not dialect.has_schema(connection, schema):  # noqa
                        connection.execute(sa.schema.CreateSchema(schema))

                for statement in self._init_statements or []:
                    connection.execute(statement)

                BaseOrmModel.REGISTRY.metadata.create_all(connection)

        session_fabric = sessionmaker(engine, expire_on_commit=False)
        self._pg = sa.orm.scoped_session(session_fabric)

    def _disconnect(self, response: flask.Response):
        return response

    def init_db(self):
        while True:
            try:
                self._logger.debug("Инициализация базы данных")
                return self._init_db()
            except Exception as e:
                self._logger.error(
                    "Ошибка инициализации базы данны, ожидание",
                    exc_info=True,
                    extra={"e": e},
                )
                time.sleep(self._init_error_timeout)

    def setup(self, app: flask.Flask):
        app.after_request(self._disconnect)
