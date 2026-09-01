from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from database import Database
from config import ADMIN_IDS

router = Router()
db = Database()

# Простая проверка на админа
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("startgame"))
async def start_game(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда только для администратора.")
        return

    state = db.get_game_state()
    if state is None:
        await message.answer("Ошибка состояния игры.")
        return
    _, is_running, _, _ = state
    if is_running:
        await message.answer("Игра уже запущена.")
        return

    db.reset_game()
    current, _, _, _ = db.get_game_state()
    await message.answer(f"🎮 Игра запущена! Начинаем с числа {current}.")

@router.message(Command("pausegame"))
async def pause_game(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда только для администратора.")
        return
    
    state = db.get_game_state()
    if state is None:
        await message.answer("Ошибка состояния игры.")
        return
    _, is_running, _, _ = state
    
    if not is_running:
        await message.answer("Игра уже приостановлена или не запущена.")
        return
    
    db.set_game_running(False)
    await message.answer("⏸ Игра приостановлена. Новые фото не принимаются.")

@router.message(Command("stopgame"))
async def stop_game(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Эта команда только для администратора.")
        return
    
    state = db.get_game_state()
    if state is None:
        await message.answer("Ошибка состояния игры.")
        return
    _, is_running, _, _ = state
    
    if not is_running:
        await message.answer("Игра уже остановлена.")
        return
    
    db.set_game_running(False)
    await message.answer("🏁 Игра завершена. Спасибо за участие!")
    
    # Показываем финальный рейтинг
    rows = db.get_rating()
    if rows:
        text = "🏆 **Финальный рейтинг:**\n\n"
        for i, (user_id, username, first_name, score) in enumerate(rows, 1):
            name = f"@{username}" if username else first_name or f"ID{user_id}"
            text += f"{i}. {name} — {score} очк.\n"
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("Нет активных игроков для отображения рейтинга.")

# Команда для проверки состояния игры (диагностика)
@router.message(Command("status"))
async def status_game(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return
    
    state = db.get_game_state()
    if state:
        current, is_running, is_voting, admin_decision = state
        await message.answer(
            f"📊 **Состояние игры:**\n"
            f"🔢 Текущее число: {current}\n"
            f"🎮 Запущена: {'✅' if is_running else '❌'}\n"
            f"🗳 Голосование: {'✅' if is_voting else '❌'}\n"
            f"⚖️ Решение админа: {'✅' if admin_decision else '❌'}"
        )
    else:
        await message.answer("Нет данных об игре.")

# Отслеживание вступления/выхода участников
@router.chat_member()
async def on_chat_member_update(update: ChatMemberUpdated):
    user = update.new_chat_member.user
    
    old_status = update.old_chat_member.status if update.old_chat_member else None
    new_status = update.new_chat_member.status if update.new_chat_member else None

    # Если пользователь вошёл
    if new_status in ("member", "administrator") and old_status in ("left", "kicked", "restricted"):
        db.add_player(user.id, user.username, user.first_name)
        db.set_player_active(user.id, True)
        await update.bot.send_message(
            chat_id=update.chat.id,
            text=f"👋 Новый участник: {user.first_name or user.username or 'Игрок'}!"
        )
    # Если вышел
    elif old_status in ("member", "administrator") and new_status in ("left", "kicked"):
        db.set_player_active(user.id, False)
        await update.bot.send_message(
            chat_id=update.chat.id,
            text=f"🚪 Участник {user.first_name or user.username or 'Игрок'} покинул группу. Отмечен как неактивный."
        )