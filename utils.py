from datetime import datetime

def is_admin(chat_member):
    # Временно закомментировано, так как ChatMemberStatus теперь в aiogram.enums
    # from aiogram.enums import ChatMemberStatus
    # return chat_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    return False  # Заглушка, если не используется

def format_player_name(user):
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Неизвестный"

def format_rating_row(rank, user_id, username, first_name, score):
    name = f"@{username}" if username else first_name or f"ID{user_id}"
    return f"{rank}. {name} — {score} очк."

def format_progress(score, total_found, last_number):
    text = f"🏅 Очки: {score}\n"
    text += f"📸 Найдено чисел: {total_found}\n"
    if last_number:
        text += f"🔢 Последнее число: {last_number}"
    else:
        text += "🔢 Пока не найдено ни одного числа."
    return text

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y %H:%M")