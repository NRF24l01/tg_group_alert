from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# Модели базы данных
class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    message = Column(String, nullable=True)
    chance = Column(Integer, default=100)  # Шанс ответа в процентах
    chat_id = Column(Integer, ForeignKey('chats.id'))
    members = relationship("GroupMember", back_populates="group")


class GroupMember(Base):
    __tablename__ = 'group_members'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String, nullable=True)  # Поле для хранения username
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group", back_populates="members")


# Создание таблиц базы данных
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Асинхронная настройка базы данных
DATABASE_URL = "sqlite+aiosqlite:///./bot.db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_sessionmaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
