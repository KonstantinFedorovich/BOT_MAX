import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List

from maxapi import Bot, Dispatcher, F
from maxapi.context import MemoryContext, State, StatesGroup
from maxapi.filters.callback_payload import CallbackPayload
from maxapi.types import (
    MessageCreated, Command, MessageCallback, CallbackButton,
    BotStarted
)
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
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


def update_user_note(user_id: int, note_id: int, updates: Dict):
    """Обновляет заметку пользователя"""
    notes = load_notes()
    user_id_str = str(user_id)

    if user_id_str in notes:
        for note in notes[user_id_str]:
            if note['id'] == note_id:
                note.update(updates)
                break
        save_notes(notes)


def delete_user_note(user_id: int, note_id: int):
    """Удаляет заметку пользователя"""
    notes = load_notes()
    user_id_str = str(user_id)

    if user_id_str in notes:
        notes[user_id_str] = [note for note in notes[user_id_str] if note['id'] != note_id]
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


# === KEYBOARDS ===
def create_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="➕ Новая заметка", payload="new_note"),
        CallbackButton(text="📝 Мои заметки", payload="list_notes")
    )
    builder.row(
        CallbackButton(text="✅ Выполненные", payload="completed_notes"),
        CallbackButton(text="🗑 Удалить все", payload="delete_all")
    )
    return builder.as_markup()


def create_notes_list_keyboard(notes: List[Dict], page: int = 0, notes_per_page: int = 5):
    """Создает клавиатуру для списка заметок с пагинацией"""
    builder = InlineKeyboardBuilder()

    start_idx = page * notes_per_page
    end_idx = start_idx + notes_per_page
    page_notes = notes[start_idx:end_idx]

    # Кнопки для заметок
    for note in page_notes:
        status = "✅" if note['completed'] else "⏳"
        builder.row(
            CallbackButton(
                text=f"{status} {note['title'][:15]}...",
                payload=NoteActionPayload(action='view', note_id=note['id']).pack()
            )
        )

    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            CallbackButton(
                text="⬅️ Назад",
                payload=ListActionPayload(action='prev', page=page - 1).pack()
            )
        )

    nav_buttons.append(
        CallbackButton(
            text="🏠 Главная",
            payload="main_menu"
        )
    )

    if end_idx < len(notes):
        nav_buttons.append(
            CallbackButton(
                text="Вперед ➡️",
                payload=ListActionPayload(action='next', page=page + 1).pack()
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    return builder.as_markup()


def create_note_actions_keyboard(note_id: int):
    """Создает клавиатуру действий для конкретной заметки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(
            text="✅ Выполнить",
            payload=NoteActionPayload(action='complete', note_id=note_id).pack()
        ),
        CallbackButton(
            text="🗑 Удалить",
            payload=NoteActionPayload(action='delete', note_id=note_id).pack()
        )
    )
    builder.row(
        CallbackButton(
            text="📋 К списку",
            payload="list_notes"
        ),
        CallbackButton(
            text="🏠 Главная",
            payload="main_menu"
        )
    )
    return builder.as_markup()


# === HANDLERS ===
@dp.bot_started()
async def on_bot_started(event: BotStarted):
    """Приветствие при первом запуске бота"""
    menu = create_main_menu()
    await bot.send_message(
        chat_id=event.chat_id,
        text="📝 Добро пожаловать в бота для заметок!\nИспользуй кнопки ниже:",
        attachments=[menu]
    )


@dp.message_created(Command('start'))
async def start_command(event: MessageCreated):
    """Главное меню бота"""
    menu = create_main_menu()
    await event.message.answer(
        text="🎯 Бот для заметок - главное меню:",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'main_menu')
async def main_menu_callback(event: MessageCallback):
    """Возврат в главное меню"""
    menu = create_main_menu()
    await event.message.answer(
        text="🎯 Главное меню:",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'new_note')
async def new_note_callback(event: MessageCallback, context: MemoryContext):
    await context.set_state(NoteStates.WAITING_TITLE)
    await event.message.answer("📝 Введите заголовок заметки:")


@dp.message_created(F.message.body.text, NoteStates.WAITING_TITLE)
async def process_title(event: MessageCreated, context: MemoryContext):
    await context.update_data(title=event.message.body.text)
    await context.set_state(NoteStates.WAITING_CONTENT)
    await event.message.answer("📄 Теперь введите содержание заметки:")


@dp.message_created(F.message.body.text, NoteStates.WAITING_CONTENT)
async def process_content(event: MessageCreated, context: MemoryContext):
    data = await context.get_data()
    user_id = event.from_user.user_id

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

    menu = create_main_menu()
    await event.message.answer(
        text=f"✅ Заметка '{data['title']}' сохранена!\nСоздано: {new_note['created_at']}",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'list_notes')
async def list_notes_callback(event: MessageCallback):
    user_id = event.from_user.user_id
    notes = get_user_notes(user_id)

    if not notes:
        await event.message.answer("📭 У вас пока нет заметок")
        return

    keyboard = create_notes_list_keyboard(notes)
    await event.message.answer(
        text="📋 Ваши заметки (выберите для действий):",
        attachments=[keyboard]
    )


@dp.message_callback(ListActionPayload.filter())
async def list_navigation_callback(event: MessageCallback, payload: ListActionPayload):
    user_id = event.from_user.user_id
    notes = get_user_notes(user_id)

    keyboard = create_notes_list_keyboard(notes, payload.page)
    await event.message.answer(
        text=f"📋 Страница {payload.page + 1}:",
        attachments=[keyboard]
    )


@dp.message_callback(NoteActionPayload.filter(F.action == 'view'))
async def view_note_callback(event: MessageCallback, payload: NoteActionPayload):
    user_id = event.from_user.user_id
    notes = get_user_notes(user_id)
    note = next((n for n in notes if n['id'] == payload.note_id), None)

    if note:
        status = "✅ ВЫПОЛНЕНА" if note['completed'] else "⏳ В РАБОТЕ"
        text = f"""📌 {note['title']}

{note['content']}

📅 Создано: {note['created_at']}
🎯 Статус: {status}"""

        keyboard = create_note_actions_keyboard(payload.note_id)
        await event.message.answer(
            text=text,
            attachments=[keyboard]
        )


@dp.message_callback(NoteActionPayload.filter(F.action == 'complete'))
async def complete_note_callback(event: MessageCallback, payload: NoteActionPayload):
    user_id = event.from_user.user_id
    update_user_note(user_id, payload.note_id, {'completed': True})

    menu = create_main_menu()
    await event.message.answer(
        text="✅ Заметка отмечена как выполненная!",
        attachments=[menu]
    )


@dp.message_callback(NoteActionPayload.filter(F.action == 'delete'))
async def delete_note_callback(event: MessageCallback, payload: NoteActionPayload):
    user_id = event.from_user.user_id
    delete_user_note(user_id, payload.note_id)

    menu = create_main_menu()
    await event.message.answer(
        text="🗑 Заметка удалена!",
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'completed_notes')
async def completed_notes_callback(event: MessageCallback):
    user_id = event.from_user.user_id
    notes = get_user_notes(user_id)
    completed_notes = [note for note in notes if note['completed']]

    if not completed_notes:
        await event.message.answer("✅ У вас нет выполненных заметок")
        return

    response = "✅ Выполненные заметки:\n\n"
    for note in completed_notes:
        response += f"🎯 {note['title']}\n"
        response += f"   📅 {note['created_at']}\n\n"

    menu = create_main_menu()
    await event.message.answer(
        text=response,
        attachments=[menu]
    )


@dp.message_callback(F.callback.payload == 'delete_all')
async def delete_all_callback(event: MessageCallback):
    user_id = event.from_user.user_id
    notes = load_notes()
    notes[str(user_id)] = []
    save_notes(notes)

    menu = create_main_menu()
    await event.message.answer(
        text="🗑 Все заметки удалены!",
        attachments=[menu]
    )


async def main():
    if not os.path.exists(NOTES_FILE):
        save_notes({})

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())