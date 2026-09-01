from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database import Database
from keyboards import get_main_menu
from utils import format_player_name, format_rating_row, format_progress

router = Router()
db = Database()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    db.add_player(user.id, user.username, user.first_name)
    await message.answer(
        f"👋 Добро пожаловать, {format_player_name(user)}!\n"
        "Это бот для игры «Охота за числами».\n"
        "Используйте меню ниже или команды администратора.",
        reply_markup=get_main_menu()
    )

@router.message(F.text == "🎮 Правила")
async def rules(message: Message):
    rules_text = (
        "📜 **Правила игры:**\n\n"
        "1. Игроки ищут числа строго по порядку от 1 до 100.\n"
        "2. Чтобы заявить число, отправьте фотографию в этот чат.\n"
        "3. Фото должно быть реальным объектом (не экран телефона/компьютера/часы).\n"
        "4. Участники голосуют за фото. Если все проголосовали «Засчитать» – число засчитывается.\n"
        "5. При голосе «Не засчитать» решение принимает администратор.\n"
        "6. За каждое засчитанное число игрок получает 1 очко.\n"
        "7. Игра продолжается до 100 (или до остановки администратором)."
    )
    await message.answer(rules_text, parse_mode="Markdown")

@router.message(F.text == "🏆 Рейтинг")
async def rating(message: Message):
    rows = db.get_rating()
    if not rows:
        await message.answer("Пока нет активных игроков.")
        return
    text = "🏆 **Рейтинг игроков:**\n\n"
    for i, (user_id, username, first_name, score) in enumerate(rows, 1):
        text += format_rating_row(i, user_id, username, first_name, score) + "\n"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🔢 Текущее число")
async def current_number(message: Message):
    state = db.get_game_state()
    if state is None:
        await message.answer("Игра ещё не запущена.")
        return
    current, is_running, is_voting, admin_decision = state
    if not is_running:
        await message.answer("⏸ Игра в данный момент не запущена.")
    else:
        status = "голосование" if is_voting else "ожидание заявки"
        await message.answer(f"🔢 Текущее число: **{current}**\nСтатус: {status}", parse_mode="Markdown")

@router.message(F.text == "📊 Статистика")
async def stats(message: Message):
    active = db.get_active_players()
    state = db.get_game_state()
    if state is None:
        await message.answer("Нет данных об игре.")
        return
    current, is_running, is_voting, admin_decision = state
    text = (
        f"📊 **Общая статистика:**\n"
        f"👥 Активных игроков: {len(active)}\n"
        f"🔢 Текущее число: {current}\n"
        f"🎮 Игра {'запущена' if is_running else 'остановлена'}\n"
        f"🗳 Голосование: {'идёт' if is_voting else 'не идёт'}"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "👤 Мой прогресс")
async def my_progress(message: Message):
    user_id = message.from_user.id
    data = db.get_player_score(user_id)
    if data is None:
        await message.answer("Вы ещё не зарегистрированы в игре. Напишите /start.")
        return
    score, total_found, last_number = data
    await message.answer(format_progress(score, total_found, last_number), parse_mode="Markdown")