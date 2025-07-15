import json
import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

router = Router()

DATA_FILE = "data.json"

class SmartPlannerStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_event_text = State()
    waiting_for_show_date = State()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"schedule": {
            "понедельник": [],
            "вторник": [],
            "среда": [],
            "четверг": [],
            "пятница": [],
            "суббота": [],
            "воскресенье": []
        }}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@router.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        "Привет! Я SmartPlannerBot 🤖\n\n"
        "Я помогу тебе управлять своим расписанием.\n\n"
        "📅 Команды:\n"
        "/add — добавить событие на конкретную дату\n"
        "/show — показать расписание на выбранную дату\n\n"
        "Я также умею показывать расписание по дням недели.\n"
        "Просто введи дату в формате ДД.ММ.ГГГГ."
    )

@router.message(F.text == "/add")
async def add_event_start(message: Message, state: FSMContext):
    await message.answer("Введи дату для события в формате `ДД.ММ.ГГГГ`\nПример: `22.07.2025`")
    await state.set_state(SmartPlannerStates.waiting_for_date)

@router.message(SmartPlannerStates.waiting_for_date)
async def add_event_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y").strftime("%d.%m.%Y")
        await state.update_data(date=date)
        await message.answer(
            "Отлично! Теперь введи время и название события через пробел.\n"
            "Пример: `14:30 Математика с репетитором`"
        )
        await state.set_state(SmartPlannerStates.waiting_for_event_text)
    except ValueError:
        await message.answer("Некорректная дата. Введи в формате `ДД.ММ.ГГГГ`, например `22.07.2025`.")

@router.message(SmartPlannerStates.waiting_for_event_text)
async def add_event_text(message: Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Пожалуйста, введи время и название события через пробел.\nПример: `14:30 Контрольная по геометрии`")
        return

    time_part, description = parts
    try:
        datetime.strptime(time_part, "%H:%M")
    except ValueError:
        await message.answer("Время должно быть в формате `ЧЧ:ММ` (например, `09:00`). Попробуй снова.")
        return

    user_data = await state.get_data()
    date = user_data["date"]
    user_id = str(message.from_user.id)

    data = load_data()
    if user_id not in data:
        data[user_id] = {}
    if date not in data[user_id]:
        data[user_id][date] = []

    data[user_id][date].append(f"{time_part} — {description}")
    data[user_id][date].sort()  # Сортировка по времени

    save_data(data)
    await message.answer(f"✅ Событие добавлено на {date}: {time_part} — {description}")
    await state.clear()

@router.message(F.text == "/show")
async def show_schedule_start(message: Message, state: FSMContext):
    await message.answer(
        "Введи дату в формате `ДД.ММ.ГГГГ`, чтобы показать расписание на этот день.\n"
        "Например: `22.07.2025`"
    )
    await state.set_state(SmartPlannerStates.waiting_for_show_date)

@router.message(SmartPlannerStates.waiting_for_show_date)
async def show_schedule_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    try:
        datetime.strptime(date_text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Пожалуйста, введи дату в правильном формате: `ДД.ММ.ГГГГ`")
        return

    user_id = str(message.from_user.id)
    data = load_data()

    user_events = data.get(user_id, {}).get(date_text, [])
    day_name = datetime.strptime(date_text, "%d.%m.%Y").strftime("%A").lower()
    school_schedule = data.get("schedule", {}).get(day_name, [])

    if not user_events and not school_schedule:
        await message.answer(f"❌ На {date_text} ничего не запланировано.")
    else:
        response = f"📅 Расписание на {date_text}:\n"
        if school_schedule:
            response += "\n📚 Уроки по расписанию:\n" + "\n".join(f"• {lesson}" for lesson in school_schedule)
        if user_events:
            response += "\n\n📝 Личные события:\n" + "\n".join(f"• {event}" for event in user_events)
        await message.answer(response)

    await state.clear()