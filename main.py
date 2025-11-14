import asyncio
import logging
from datetime import datetime

from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated, Command, MessageCallback, CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.filters import F

logging.basicConfig(level=logging.INFO)

bot = Bot('f9LHodD0cOIldjpxJWwsW9WZj9R7gYvK7Tt5042DZ7JBxEDrCmGmdzu4CaYjwR4pfyCfeMGT-K4R_eVr4WIK')
dp = Dispatcher()

# Временное хранилище (позже заменим на БД)
user_notes = {}


# === KEYBOARDS ===
def create_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="➕ Новая заметка", payload="new_note"),
        CallbackButton(text="📝 Мои заметки", payload="list_notes")
    )
    builder.row(
        CallbackButton(text="✅ Выполненные", payload="completed_notes"),
        CallbackButton(text="⚙️ Настройки", payload="settings")
    )
    return builder.as_markup()


# === HANDLERS ===
@dp.bot_started()
async def on_bot_started(event):
    """Приветствие при первом запуске бота"""
    await bot.send_message(
        chat_id=event.chat_id,
        text="📝 Добро пожаловать в бота для заметок!\nИспользуй /start для начала работы"
    )


@dp.message_created(Command('start'))
async def start_command(event: MessageCreated):
    """Главное меню бота"""
    menu = create_main_menu()
    await event.message.answer(
        text="🎯 Главное меню заметочника:",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'new_note')
async def new_note_callback(event: MessageCallback):
    """Начало создания новой заметки"""
    await event.answer(new_text="Введите заголовок заметки:")
    # Здесь будет логика перехода в состояние WAITING_TITLE


@dp.message_callback(F.callback.payload == 'list_notes')
async def list_notes_callback(event: MessageCallback):
    """Показать список заметок"""
    user_id = event.from_user.id
    notes = user_notes.get(user_id, [])

    if not notes:
        await event.answer(new_text="📭 У вас пока нет заметок")
        return

    response = "📋 Ваши заметки:\n\n"
    for i, note in enumerate(notes, 1):
        response += f"{i}. {note['title']}\n"

    await event.answer(new_text=response)


async def main():
    await dp.start_polling(bot)


#if __name__ == '__main__':
#    asyncio.run(main())