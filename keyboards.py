from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Постоянная клавиатура меню
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Правила")],
            [KeyboardButton(text="🏆 Рейтинг")],
            [KeyboardButton(text="🔢 Текущее число")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👤 Мой прогресс")]
        ],
        resize_keyboard=True
    )

# Inline-клавиатура для голосования
def get_vote_keyboard(submission_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Засчитать", callback_data=f"vote_approve_{submission_id}"),
                InlineKeyboardButton(text="❌ Не засчитать", callback_data=f"vote_reject_{submission_id}")
            ]
        ]
    )

# Клавиатура для администратора при спорном решении
def get_admin_decision_keyboard(submission_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Засчитать", callback_data=f"admin_accept_{submission_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject_{submission_id}")
            ]
        ]
    )