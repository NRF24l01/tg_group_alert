import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram import types
from aiogram.utils import markdown
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from config import TOKEN, ADMINS
from model import *
from functools import wraps

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Настройка базы данных
Base = declarative_base()
engine = create_async_engine('sqlite+aiosqlite:///bot.db')
async_sessionmaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Создание таблиц базы данных
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Декоратор для проверки прав администратора
def admin_only(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in ADMINS:
            await message.reply("У вас нет прав для использования этой команды.")
            return
        return await func(message, *args, **kwargs)

    return wrapper


# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "Привет! Я бот для управления группами.\n"
        "Используй команду /help, чтобы узнать, как я могу помочь!"
    )


# Команда /help
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.reply(
        "/register - Зарегистрировать чат в базе данных\n"
        "/group <действие> <название группы|id группы> - Управление группами\n"
        "  Действия:\n"
        "    create - создать группу\n"
        "    remove - удалить группу\n"
        "    add - добавить участника в группу (ответом на сообщение или по id)\n"
        "    del - удалить участника из группы (ответом на сообщение или по id)\n"
        "    show - показать информацию о группе\n"
        "    set_message - задать сообщение для группы\n"
        "    set_chance - задать вероятность ответа группы\n"
        "/group list - показать все группы в этом чате\n"
        "\n"
        "Только администраторы могут управлять группами."
    )


# Команда /register - регистрация чата
@dp.message_handler(commands=['register'])
@admin_only
async def register_chat(message: types.Message):
    async with async_sessionmaker() as session:
        async with session.begin():
            result = await session.execute(select(Chat).filter_by(chat_id=message.chat.id))
            chat = result.scalars().first()

            if not chat:
                new_chat = Chat(chat_id=message.chat.id)
                session.add(new_chat)
                await session.commit()
                await message.reply("Чат успешно зарегистрирован!")
            else:
                await message.reply("Чат уже зарегистрирован.")


# Функция для экранирования специальных символов
def escape_markdown(text):
    return text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(',
                                                                                                        '\\(').replace(
        ')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+',
                                                                                                            '\\+').replace(
        '-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.',
                                                                                                            '\\.').replace(
        '!', '\\!')


# Команда /group для управления группами
@dp.message_handler(commands=['group'])
@admin_only
async def manage_group(message: types.Message):
    args = message.get_args().split()

    if len(args) < 2:
        await message.reply("Недостаточно аргументов. Пример: /group <действие> <название группы|id группы>.")
        return

    action = args[0]
    group_identifier = ' '.join(args[1:])  # Объединяем оставшиеся аргументы для названия группы

    async with async_sessionmaker() as session:
        async with session.begin():
            result = await session.execute(select(Chat).filter_by(chat_id=message.chat.id))
            chat = result.scalars().first()

            if not chat:
                await message.reply("Чат не зарегистрирован. Используйте /register.")
                return

            # Проверка, является ли идентификатор числом (ID группы)
            if group_identifier.isdigit():
                group_result = await session.execute(select(Group).filter_by(id=int(group_identifier), chat_id=chat.id))
            else:
                group_result = await session.execute(select(Group).filter_by(name=group_identifier, chat_id=chat.id))

            group = group_result.scalars().first()

            if action == 'create':
                if not group:
                    new_group = Group(name=group_identifier, chat_id=chat.id)
                    session.add(new_group)
                    await session.commit()
                    await message.reply(f"Группа {escape_markdown(group_identifier)} успешно создана.")
                else:
                    await message.reply("Группа с таким названием уже существует.")

            elif action == 'remove':
                if group:
                    await session.delete(group)
                    await session.commit()
                    await message.reply(f"Группа {escape_markdown(group_identifier)} успешно удалена.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'add':
                if group:
                    if message.reply_to_message:
                        user_id = message.reply_to_message.from_user.id
                        username = message.reply_to_message.from_user.username  # Получаем username

                        # Проверяем, существует ли уже этот участник
                        member_result = await session.execute(
                            select(GroupMember).filter_by(user_id=user_id, group_id=group.id))
                        member = member_result.scalars().first()

                        if member:
                            member.username = username  # Обновляем username
                        else:
                            member = GroupMember(user_id=user_id, username=username, group_id=group.id)
                            session.add(member)

                        await session.commit()
                        await message.reply(
                            f"Пользователь @{escape_markdown(username or 'неизвестен')} добавлен в группу {escape_markdown(group.name)}.")
                    elif len(args) == 3 and args[2].isdigit():  # Проверка, если указан id пользователя
                        user_id = int(args[2])
                        username = None  # Username не известен, так как это ID

                        # Добавление участника по ID
                        member_result = await session.execute(
                            select(GroupMember).filter_by(user_id=user_id, group_id=group.id))
                        member = member_result.scalars().first()

                        if not member:
                            member = GroupMember(user_id=user_id, username=username, group_id=group.id)
                            session.add(member)
                            await session.commit()
                            await message.reply(
                                f"Пользователь с ID {user_id} добавлен в группу {escape_markdown(group.name)}.")
                        else:
                            await message.reply("Пользователь уже состоит в группе.")
                    else:
                        await message.reply(
                            "Эта команда должна быть ответом на сообщение пользователя или указанием ID пользователя.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'del':
                if group:
                    if message.reply_to_message:
                        user_id = message.reply_to_message.from_user.id

                        member_result = await session.execute(
                            select(GroupMember).filter_by(user_id=user_id, group_id=group.id))
                        member = member_result.scalars().first()

                        if member:
                            await session.delete(member)
                            await session.commit()
                            await message.reply(f"Пользователь удален из группы {escape_markdown(group.name)}.")
                        else:
                            await message.reply("Пользователь не найден в группе.")
                    elif len(args) == 3 and args[2].isdigit():  # Проверка, если указан id пользователя
                        user_id = int(args[2])

                        member_result = await session.execute(
                            select(GroupMember).filter_by(user_id=user_id, group_id=group.id))
                        member = member_result.scalars().first()

                        if member:
                            await session.delete(member)
                            await session.commit()
                            await message.reply(
                                f"Пользователь с ID {user_id} удален из группы {escape_markdown(group.name)}.")
                        else:
                            await message.reply("Пользователь не найден в группе.")
                    else:
                        await message.reply(
                            "Эта команда должна быть ответом на сообщение пользователя или указанием ID пользователя.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'show':
                if group:
                    members_result = await session.execute(select(GroupMember).filter_by(group_id=group.id))
                    members = members_result.scalars().all()

                    # Создаем список кликабельных пользователей
                    member_list = []
                    for member in members:
                        username = member.username or str(member.user_id)
                        # Экранируем специальные символы
                        escaped_username = (
                            username
                            .replace('(', r'\(')
                            .replace(')', r'\)')
                            .replace('_', r'\_')
                            .replace('*', r'\*')
                            .replace('[', r'\[')
                            .replace(']', r'\]')
                            .replace('~', r'\~')
                            .replace('>', r'\>')
                            .replace('#', r'\#')
                            .replace('+', r'\+')
                            .replace('-', r'\-')
                            .replace('=', r'\=')
                            .replace('|', r'\|')
                            .replace('{', r'\{')
                            .replace('}', r'\}')
                            .replace('.', r'\.')
                            .replace('!', r'\!')
                        )
                        member_list.append(f"[{escaped_username}](tg://user?id={member.user_id})")

                    member_count = len(members)

                    msg = f"Информация о группе *{group.name}* (ID: {group.id}):\n" + f"Количество участников: {member_count}\n" + f"Участники: {', '.join(member_list) if member_list else 'Нет участников.'}"

                    await message.reply(
                        msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'set_message':
                if group:
                    group.message = ' '.join(args[2:])
                    await session.commit()
                    await message.reply(f"Сообщение для группы *{escape_markdown(group.name)}* установлено.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'set_chance':
                print(args, group)
                if group and len(args) == 3 and args[2].isdigit():
                    group.chance = int(args[2])
                    await session.commit()
                    await message.reply(
                        f"Вероятность ответа для группы *{escape_markdown(group.name)}* установлена на {group.chance}%.")
                else:
                    await message.reply("Группа не найдена или неправильное значение шанса.")


# Команда /group list - показать все группы в чате
@dp.message_handler(commands=['group', 'list'])
@admin_only
async def list_groups(message: types.Message):
    async with async_sessionmaker() as session:
        async with session.begin():
            result = await session.execute(select(Chat).filter_by(chat_id=message.chat.id))
            chat = result.scalars().first()

            if not chat:
                await message.reply("Чат не зарегистрирован. Используйте /register.")
                return

            group_results = await session.execute(select(Group).filter_by(chat_id=chat.id))
            groups = group_results.scalars().all()

            if groups:
                group_list = [f"ID: {group.id}, Название: {group.name}, Участников: {len(group.members)}" for group in
                              groups]
                await message.reply("Список групп:\n" + "\n".join(group_list))
            else:
                await message.reply("Группы не найдены.")


# Обновление username пользователей
@dp.message_handler()
async def update_username(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id

    async with async_sessionmaker() as session:
        async with session.begin():
            result = await session.execute(select(Chat).filter_by(chat_id=chat_id))
            chat = result.scalars().first()

            if chat:
                group_results = await session.execute(
                    select(Group).join(GroupMember).filter(GroupMember.user_id == user_id, Group.chat_id == chat.id))
                groups = group_results.scalars().all()

                for group in groups:
                    # Обновляем username пользователя в базе
                    member_result = await session.execute(
                        select(GroupMember).filter_by(user_id=user_id, group_id=group.id))
                    member = member_result.scalars().first()

                    if member:
                        if member.username != username:  # Обновляем только если изменился
                            member.username = username
                            await session.commit()

                    if group.chance > random.random() * 100:
                        await message.reply(group.message)


# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    import asyncio


    async def on_startup(dp):
        await create_db()


    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
