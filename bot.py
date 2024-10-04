import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from config import TOKEN, ADMINS
from model import *
from functools import wraps


# Декоратор для проверки прав администратора
def admin_only(func):
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in ADMINS:
            await message.reply("У вас нет прав для использования этой команды.")
            return
        return await func(message, *args, **kwargs)

    return wrapper


bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply(
        "Привет! Я бот для управления группами.\n"
        "Используй команду /help, чтобы узнать, как я могу помочь!"
    )


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.reply(
        "/register - Зарегистрировать чат в базе данных\n"
        "/group <действие> <название группы> - Управление группами\n"
        "  Действия:\n"
        "    create - создать группу\n"
        "    remove - удалить группу\n"
        "    add - добавить участника в группу (ответом на сообщение)\n"
        "    del - удалить участника из группы (ответом на сообщение)\n"
        "    show - показать информацию о группе\n"
        "    set_message - задать сообщение для группы\n"
        "    set_chance - задать вероятность ответа группы\n"
        "\n"
        "Только администраторы могут управлять группами.\n"
        "Для подробной информации по каждой команде используйте соответствующую документацию."
    )


# Команда /register для добавления чата в базу данных
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


# Команда для управления группами
@dp.message_handler(commands=['group'])
@admin_only
async def manage_group(message: types.Message):
    args = message.get_args().split()

    if len(args) < 2:
        await message.reply("Недостаточно аргументов. Пример: /group <действие> <название группы>.")
        return

    action = args[0]
    group_name = args[1]

    async with async_sessionmaker() as session:
        async with session.begin():
            result = await session.execute(select(Chat).filter_by(chat_id=message.chat.id))
            chat = result.scalars().first()

            if not chat:
                await message.reply("Чат не зарегистрирован. Используйте /register.")
                return

            group_result = await session.execute(select(Group).filter_by(name=group_name, chat_id=chat.id))
            group = group_result.scalars().first()

            if action == 'create':
                if not group:
                    new_group = Group(name=group_name, chat_id=chat.id)
                    session.add(new_group)
                    await session.commit()
                    await message.reply(f"Группа {group_name} успешно создана.")
                else:
                    await message.reply("Группа с таким названием уже существует.")

            elif action == 'remove':
                if group:
                    await session.delete(group)
                    await session.commit()
                    await message.reply(f"Группа {group_name} удалена.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'add':
                if group:
                    if message.reply_to_message:
                        user_id = message.reply_to_message.from_user.id
                        member = GroupMember(user_id=user_id, group_id=group.id)
                        session.add(member)
                        await session.commit()
                        await message.reply(f"Пользователь добавлен в группу {group_name}.")
                    else:
                        await message.reply("Эта команда должна быть ответом на сообщение пользователя.")
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
                            await message.reply(f"Пользователь удалён из группы {group_name}.")
                        else:
                            await message.reply("Пользователь не найден в группе.")
                    else:
                        await message.reply("Эта команда должна быть ответом на сообщение пользователя.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'show':
                if group:
                    members_result = await session.execute(select(GroupMember).filter_by(group_id=group.id))
                    members = members_result.scalars().all()
                    member_list = ', '.join([str(member.user_id) for member in members])
                    response = f"Группа {group_name}:\nУчастники: {member_list or 'нет участников'}\nСообщение: {group.message or 'не установлено'}\nШанс ответа: {group.chance * 100}%"
                    await message.reply(response)
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'set_message' and len(args) > 2:
                if group:
                    group.message = ' '.join(args[2:])
                    await session.commit()
                    await message.reply(f"Сообщение для группы {group_name} установлено.")
                else:
                    await message.reply("Группа не найдена.")

            elif action == 'set_chance' and len(args) == 3:
                if group:
                    try:
                        chance = float(args[2])
                        if 0 <= chance <= 1:
                            group.chance = chance
                            await session.commit()
                            await message.reply(f"Шанс для группы {group_name} установлен на {chance * 100}%.")
                        else:
                            await message.reply("Шанс должен быть от 0 до 1.")
                    except ValueError:
                        await message.reply("Неверный формат шанса.")
                else:
                    await message.reply("Группа не найдена.")


# Функция для проверки сообщений и ответов
@dp.message_handler()
async def check_message(message: types.Message):
    user_id = message.from_user.id
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
                    if group.chance > random.random():
                        await message.reply(group.message)


if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
