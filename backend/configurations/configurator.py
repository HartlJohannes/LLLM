import sqlalchemy as sql
from sqlalchemy import Table, Column, Integer, String, MetaData
from typing import Any
from pathlib import Path

THIS_DIR = Path(__file__).parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{THIS_DIR}/database.sqlite"

engine = sql.create_engine(SQLALCHEMY_DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

tables = {
    "configurations": Table(
        "configurations", metadata,
        Column("uid", Integer, primary_key=True),
        Column("agent_count", Integer),
        Column("supervisor_count", Integer),
        extend_existing=True,
    ),
    "datasources": Table(
        "datasources", metadata,
        Column("uid", Integer, primary_key=True),
        Column("config_uid", Integer),
        Column("url", String),
        extend_existing=True,
    ),
}

# create tables if not exist
metadata.create_all(bind=engine)


class Configuration:
    """
    A class to represent a LLM configuration in the database
    """

    def __init__(self, agent_count: int, supervisor_count: int, uid: int = None):
        self.uid = uid
        self.agent_count = agent_count
        self.supervisor_count = supervisor_count
        self._datasources = None

    @staticmethod
    def grab(uid: int) -> Any | None:
        """
        Grabs the configuration from the database

        :param uid: uid of the configuration in the database
        :return: Configuration object or None if not found
        """
        # table for configurations
        cfg_table = tables["configurations"]
        # search in database
        with engine.connect() as conn:
            result = conn.execute(
                sql.select(cfg_table.c.agent_count, cfg_table.c.supervisor_count).where(cfg_table.c.uid == uid)
            )
            row = result.first()
            if row:
                return Configuration(agent_count=row[0], supervisor_count=row[1], uid=uid)
        return None

    def save(self) -> None:
        """
        Save configuration to file:
        - update if already existent
        - otherwise insert into database

        :return: None
        """
        # table for configurations
        cfg_table = tables["configurations"]

        with engine.connect() as conn:
            if not self.exists:
                # if object is not in database, create the object
                rows = conn.execute(
                    cfg_table.insert().values(
                        uid=self.uid,
                        agent_count=self.agent_count,
                        supervisor_count=self.supervisor_count,
                    )
                )
                self.uid = rows.inserted_primary_key[0]
            else:
                # update object (row) in database
                conn.execute(
                    cfg_table.update().where(cfg_table.c.uid == self.uid).values(
                        agent_count=self.agent_count,
                        supervisor_count=self.supervisor_count,
                    )
                )
            conn.commit()

    def delete(self) -> bool:
        """
        Delete the configuration from the database

        :return: True if deleted, False if not found
        """
        # if configuration does not exist, return False
        if not self.exists:
            return False

        # table for configurations
        cfg_table = tables["configurations"]
        # remove the configuration from database
        with engine.connect() as conn:
            conn.execute(
                sql.delete(cfg_table).where(cfg_table.c.uid == self.uid)
            )
            conn.commit()
        return True

    @property
    def exists(self) -> bool:
        """
        Checks whether the configuration (this object, only checks uid) exists in the database

        :return: True if exists (found), False otherwise
        """
        # table for configurations
        cfg_table: Table = tables["configurations"]
        with engine.connect() as conn:
            result = conn.execute(
                sql.select(cfg_table.c.uid).where(cfg_table.c.uid == self.uid)
            )
            return True if result.first() else False

    @property
    def datasources(self) -> list[str]:
        """
        Get the datasources for this configuration

        :return: list of datasources
        """
        # table for datasources
        ds_table: Table = tables["datasources"]
        if self._datasources is None:
            with engine.connect() as conn:
                result = conn.execute(
                    sql.select(ds_table.c.url).where(ds_table.c.config_uid == self.uid)
                )
                self._datasources = [row[0] for row in result]

        return self._datasources

    @datasources.setter
    def datasources(self, value: list[str]) -> None:
        """
        Set the datasources for this configuration:
        - first deletes all datasources for this configuration
        - then adds all of them back into the database

        :param value: new datasources
        :return: None
        """
        if not isinstance(value, list):
            raise ValueError("Datasources must be of type list[str]")

        # table for datasources
        ds_table = tables["datasources"]

        # delete all datasources
        with engine.connect() as conn:
            conn.execute(
                sql.delete(ds_table).where(ds_table.c.config_uid == self.uid)
            )
            conn.commit()

        self._datasources = value

        # add all of them back in
        with engine.connect() as conn:
            for datasource in self._datasources:
                conn.execute(
                    ds_table.insert().values(
                        config_uid=self.uid,
                        url=datasource,
                    )
                )
            conn.commit()

    @staticmethod
    def list():
        """
        List all configurations in the database

        :return: list of configurations
        """
        # table for configurations
        cfg_table: Table = tables["configurations"]
        with engine.connect() as conn:
            result = conn.execute(
                sql.select(cfg_table.c.uid)
            )
            return [row[0] for row in result]

    def __repr__(self):
        return f"Configuration(agent_count={self.agent_count}, supervisor_count={self.supervisor_count}, uid={self.uid})"


if __name__ == '__main__':
    # do some tests
    test1 = Configuration.grab(2)
    test1.datasources += ["http://localhost:8080"]
    test1.save()
    print(test1)
    print(test1.datasources)