import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql.expression import select
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import BigInteger

from . import cfg, utils

Base = declarative_base()
db_engine = create_async_engine(cfg.db_url_async, connect_args=cfg.db_connect_args)
db_session = sessionmaker(db_engine, **cfg.db_session_kwargs)


class MirroredMessage(Base):
    __tablename__ = "mirrored_message"
    __mapper_args__ = {"eager_defaults": True}
    dest_msg = Column("dest_msg", BigInteger, primary_key=True)
    dest_channel = Column("dest_ch", BigInteger)
    source_msg = Column("source_msg", BigInteger)
    source_channel = Column("src_ch", BigInteger)

    def __init__(self, dest_msg, dest_channel, source_msg, source_channel):
        super().__init__()
        self.dest_msg = int(dest_msg)
        self.dest_channel = int(dest_channel)
        self.source_msg = int(source_msg)
        self.source_channel = int(source_channel)

    @classmethod
    @utils.ensure_session(db_session)
    async def add_msg(
        cls, dest_msg, dest_channel, source_msg, source_channel, session=None
    ):
        """Create a session, begin it and add a message pair"""
        message_pair = cls(dest_msg, dest_channel, source_msg, source_channel)
        session.add(message_pair)
        return message_pair

    @classmethod
    @utils.ensure_session(db_session)
    async def get_dest_msgs_and_channels(
        cls,
        source_msg: int,
        session=None,
    ):
        """Return dest message and channel ids from source message id"""
        dest_msgs = (
            await session.execute(
                select(cls.dest_msg, cls.dest_channel).where(
                    cls.source_msg == source_msg
                )
            )
        ).fetchall()
        # Handle source_id not found
        dest_msgs = [] if dest_msgs is None else dest_msgs
        return dest_msgs


async def recreate_all():
    # db_engine = create_engine(cfg.db_url, connect_args=cfg.db_connect_args)
    db_engine = create_async_engine(cfg.db_url_async, connect_args=cfg.db_connect_args)
    # db_session = sessionmaker(db_engine, **cfg.db_session_kwargs)

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(recreate_all())
