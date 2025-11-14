import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List

from maxapi import Bot, Dispatcher, F
from maxapi.context import MemoryContext, State, StatesGroup
from maxapi.filters.callback_payload import CallbackPayload
from maxapi.filters.middleware import BaseMiddleware
from maxapi.types import (
    MessageCreated, Command, MessageCallback, CallbackButton,
    BotStarted
)
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

bot = Bot('f9LHodD0cOIldjpxJWwsW9WZj9R7gYvK7Tt5042DZ7JBxEDrCmGmdzu4CaYjwR4pfyCfeMGT-K4R_eVr4WIK')
dp = Dispatcher()

# Файл для хранения заметок
NOTES_FILE = "user_notes.json"


# === ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛАМИ ===
def load_notes() -> Dict[str, List[Dict]]:
    """Загружает заметки из файла"""
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def save_notes(notes: Dict[str, List[Dict]]):
    """Сохраняет заметки в файл"""
    with open(NOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def get_user_notes(user_id: int) -> List[Dict]:
    """Получает заметки конкретного пользователя"""
    notes = load_notes()
    return notes.get(str(user_id), [])


def save_user_note(user_id: int, note: Dict):
    """Сохраняет заметку пользователя"""
    notes = load_notes()
    user_id_str = str(user_id)

    if user_id_str not in notes:
        notes[user_id_str] = []

    notes[user_id_str].append(note)
    save_notes(notes)


# === PAYLOADS ===
class NoteActionPayload(CallbackPayload, prefix='note'):
    action: str  # 'view', 'edit', 'delete', 'complete'
    note_id: int


class ListActionPayload(CallbackPayload, prefix='list'):
    action: str  # 'prev', 'next', 'back'
    page: int


# === STATES ===
class NoteStates(StatesGroup):
    WAITING_TITLE = State()
    WAITING_CONTENT = State()
    WAITING_DEADLINE = State()


# === MIDDLEWARE ===
class UserInitMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.user_id  # ИСПРАВЛЕНО: user_id вместо id
        # Гарантируем что у пользователя есть запись в файле
        notes = load_notes()
        if str(user_id) not in notes:
            notes[str(user_id)] = []
            save_notes(notes)
        return await handler(event, data)


# === KEYBOARDS ===
def create_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="➕ Новая заметка", payload="new_note"),
        CallbackButton(text="📝 Мои заметки", payload="list_notes")
    )
    builder.row(
        CallbackButton(text="✅ Выполненные", payload="completed_notes"),
        CallbackButton(text="📊 Статистика", payload="stats")
    )
    return builder.as_markup()


# === HANDLERS ===
@dp.bot_started()
async def on_bot_started(event: BotStarted):
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
        text="🎯 Бот для заметок - главное меню:",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'new_note')
async def new_note_callback(event: MessageCallback, context: MemoryContext):
    await context.set_state(NoteStates.WAITING_TITLE)
    await event.answer(new_text="📝 Введите заголовок заметки:")


@dp.message_created(F.message.body.text, NoteStates.WAITING_TITLE)
async def process_title(event: MessageCreated, context: MemoryContext):
    await context.update_data(title=event.message.body.text)
    await context.set_state(NoteStates.WAITING_CONTENT)
    await event.message.answer("📄 Теперь введите содержание заметки:")


@dp.message_created(F.message.body.text, NoteStates.WAITING_CONTENT)
async def process_content(event: MessageCreated, context: MemoryContext):
    data = await context.get_data()
    user_id = event.from_user.user_id  # ИСПРАВЛЕНО: user_id вместо id

    # Создаем новую заметку
    user_notes = get_user_notes(user_id)
    new_note = {
        'id': len(user_notes) + 1,
        'title': data['title'],
        'content': event.message.body.text,
        'created_at': datetime.now().strftime("%d.%m.%Y в %H:%M"),
        'completed': False
    }

    # Сохраняем в файл
    save_user_note(user_id, new_note)

    await context.clear()
    await event.message.answer(f"✅ Заметка '{data['title']}' сохранена!\n\nСоздано: {new_note['created_at']}")


@dp.message_callback(F.callback.payload == 'list_notes')
async def list_notes_callback(event: MessageCallback):
    """Показать список заметок"""
    user_id = event.from_user.user_id  # ИСПРАВЛЕНО: user_id вместо id
    notes = get_user_notes(user_id)

    if not notes:
        await event.answer(new_text="📭 У вас пока нет заметок")
        return

    response = "📋 Ваши заметки:\n\n"
    for note in notes:
        status = "✅" if note['completed'] else "⏳"
        response += f"{status} {note['title']}\n"
        response += f"   📅 {note['created_at']}\n"
        response += f"   📄 {note['content'][:50]}{'...' if len(note['content']) > 50 else ''}\n\n"

    await event.answer(new_text=response)


@dp.message_callback(F.callback.payload == 'completed_notes')
async def completed_notes_callback(event: MessageCallback):
    """Показать выполненные заметки"""
    user_id = event.from_user.user_id  # ИСПРАВЛЕНО: user_id вместо id
    notes = get_user_notes(user_id)
    completed_notes = [note for note in notes if note['completed']]

    if not completed_notes:
        await event.answer(new_text="✅ У вас нет выполненных заметок")
        return

    response = "✅ Выполненные заметки:\n\n"
    for note in completed_notes:
        response += f"🎯 {note['title']}\n"
        response += f"   📅 {note['created_at']}\n\n"

    await event.answer(new_text=response)


async def main():
    # Создаем файл если его нет
    if not os.path.exists(NOTES_FILE):
        save_notes({})

    await dp.start_polling(bot)


#if __name__ == '__main__':
#    asyncio.run(main())