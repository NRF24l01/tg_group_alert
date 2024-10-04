from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Модель для чата
class Chat(Base):
    __tablename__ = 'chats'
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)

# Модель для группы
class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    message = Column(String, nullable=True)
    chance = Column(Float, default=0.0)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    chat = relationship("Chat", back_populates="groups")
    members = relationship("GroupMember", back_populates="group")

# Модель для участников группы
class GroupMember(Base):
    __tablename__ = 'group_members'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group", back_populates="members")

Chat.groups = relationship("Group", order_by=Group.id, back_populates="chat")

# Асинхронная настройка базы данных
DATABASE_URL = "sqlite+aiosqlite:///./bot.db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_sessionmaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
