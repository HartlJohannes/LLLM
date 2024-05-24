from agents import Team, SupervisorRole, ChatRole
from uuid import uuid4
import sqlalchemy as sql
from sqlalchemy import Table, Column, Integer, String, MetaData, Text
from pathlib import Path
import pickle
from configurations import Configuration


THIS_DIR = Path(__file__).parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{THIS_DIR}/sessions.sqlite"

engine = sql.create_engine(SQLALCHEMY_DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)

tables = {
    "sessions": Table(
        "sessions", metadata,
        Column("uid", Integer, primary_key=True),
        Column("config_uid", Integer),
        Column("session_key", String),
        Column("name", String, nullable=True),
        Column("team", Text, nullable=False),
        extend_existing=True,
    ),
}

# create tables if not exist
metadata.create_all(bind=engine)


class Session:
    def __init__(self, config_uid: int, session_key: str | None = None, uid: int | None = None, name: str | None = None):
        # configuration uid
        self.config_uid = config_uid
        # session key
        self.key = session_key or self.__gen_session_key()
        # session uid
        self.uid = uid
        # name
        self.name = name

        self._config = Configuration.grab(config_uid)
        self._agent_count = self._config.agent_count
        self._supervisor_count = self._config.supervisor_count
        self._team = None

    @property
    def exists(self) -> bool:
        return True if Session.grab(self.config_uid) else False

    @property
    def team(self):
        if self._team:
            # team already loaded into memory
            return self._team
        print(self.exists)
        if self.exists:
            # find the team in database and load it into memory
            with engine.connect() as conn:
                pickle_team = conn.execute(
                    sql.select(tables["sessions"].c.team).where(tables["sessions"].c.uid == self.uid)
                ).first()[0]
                self._team = pickle.loads(pickle_team, fix_imports=True, encoding="ASCII", errors="strict", buffers=None)
                return self._team

        else:
            # create a new team
            agents = [ChatRole() for i in range(self._agent_count)]
            supervisors = [SupervisorRole() for i in range(self._supervisor_count)]
            self._team = Team(agents=agents, supervisors=supervisors)
            self.save()
            return self._team

    async def send(self, msg):
        """
        Send a message to the team

        :param msg: message to send
        :return: None
        """
        await self.team(msg)

    def save(self) -> None:
        """
        Saves the session into the database

        :return: None
        """
        # table for sessions
        session_table = tables["sessions"]

        if not self.team:
            # will save automatically due to save call in self.team()
            # but makes sure that self._team is set when saving
            return

        with engine.connect() as conn:
            if self.exists:
                # update row in database
                rows = conn.execute(
                    session_table.update().where(session_table.c.uid == self.uid).values(
                        session_key=self.key,
                        config_uid=self.config_uid,
                        team=pickle.dumps(self._team, protocol=None, fix_imports=True, buffer_callback=None),
                        name=self.name
                    )
                )
                self.uid = rows.inserted_primary_key[0]
            else:
                # insert row into database
                conn.execute(
                    session_table.insert().values(
                        config_uid=self.config_uid,
                        session_key=self.key,
                        team=pickle.dumps(self._team, protocol=None, fix_imports=True, buffer_callback=None),
                        name=self.name
                    )
                )
                conn.commit()

    @property
    def config(self):
        return self._config

    def delete(self) -> bool:
        """
        Delete the session from the database

        :return: whether the session was deleted
        """
        if not self.exists:
            return False

        # table for sessions
        session_table = tables["sessions"]

        with engine.connect() as conn:
            conn.execute(
                sql.delete(session_table).where(session_table.c.uid == self.uid)
            )
            conn.commit()
        return True

    @staticmethod
    def list() -> list[str]:
        """
        Retrieve a list of all session keys

        :return: session keys
        """
        # table for sessions
        session_table = tables["sessions"]
        # search in database
        with engine.connect() as conn:
            rows = conn.execute(
                sql.select(session_table.c.session_key)
            )
        return [row[0] for row in rows]



    @staticmethod
    def grab(uid: int):
        """
        Grab a session from the database using the uid

        :param uid: uid of the session
        :return: Session object or None if not found
        """
        # table for sessions
        session_table = tables["sessions"]
        # search in database
        with engine.connect() as conn:
            row = conn.execute(
                sql.select(
                    session_table.c.config_uid,
                    session_table.c.session_key,
                    session_table.c.name
                ).where(session_table.c.uid == uid)
            ).first()
            if not row:
                return None
            return Session(row[0],  row[1], name=row[2])

    @staticmethod
    def find(session_key: str):
        """
        Grab a session from the database using the session key

        :param session_key: Session key
        :return: Session object or None if not found
        """
        # table for sessions
        session_table = tables["sessions"]
        # search in database
        with engine.connect() as conn:
            row = conn.execute(
                sql.select(
                    session_table.c.config_uid,
                    session_table.c.session_key,
                    session_table.c.name
                ).where(session_table.c.session_key == session_key)
            ).first()
            if not row:
                return None
            return Session(row[0], row[1], name=row[2])

    @staticmethod
    def __gen_session_key():
        return str(uuid4())

    def __repr__(self):
        return f'<Session: {self.key}>'


class Cache:
    cache: dict[str, Session] = dict()
    @staticmethod
    def find(session_key: str) -> Session | None:
        """
        Find a session in the cache

        :param session_key: session key
        :return: Session object or None if not found
        """
        return Cache.cache.get(session_key)

    @staticmethod
    def check(session_key: str) -> bool:
        """
        Checks whether a session is in the cache

        :param session_key:
        :return: True if found, False otherwise
        """
        return session_key in Cache.cache

    @staticmethod
    def add(session: Session) -> None:
        """
        Add a session to the cache

        :param session: Session object
        :return: None
        """
        Cache.cache[session.key] = session


    @staticmethod
    def locate(session_key: str) -> Session | None:
        """
        Locate a session in cache or from db

        :param session_key: session key
        :return: the session or none
        """
        if Cache.check(session_key):
            return Cache.find(session_key)
        else:
            return Session.find(session_key)
