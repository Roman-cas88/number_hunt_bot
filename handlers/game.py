from aiogram import Router, types
from aiogram import F
from aiogram.types import Message, CallbackQuery
from database import Database
from keyboards import get_vote_keyboard, get_admin_decision_keyboard, get_main_menu
from utils import format_player_name, is_admin
from config import ADMIN_IDS
import asyncio

router = Router()
db = Database()

# Флаг для фоновых задач напоминаний – запускаем один раз
reminder_task_started = False

@router.message(F.photo)
async def handle_photo(message: Message):
    user = message.from_user
    state = db.get_game_state()
    if state is None:
        await message.answer("Ошибка состояния игры.")
        return

    current_number, is_running, is_voting, admin_decision = state

    if not is_running:
        await message.answer("⏸ Игра не запущена или приостановлена. Дождитесь команды /startgame.")
        return
    if is_voting:
        await message.answer("⏳ Сейчас идёт голосование за предыдущее число. Подождите.")
        return
    if admin_decision:
        await message.answer("⚖️ Администратор ещё не принял решение по предыдущему фото. Подождите.")
        return

    # Проверяем, что это фото (есть file_id)
    if not message.photo:
        return

    # Создаём заявку
    photo_file_id = message.photo[-1].file_id
    # Отправляем сообщение с фото и голосованием
    caption = f"📸 {format_player_name(user)} нашёл число {current_number}. Подтвердите фотографию."
    sent_msg = await message.answer_photo(
        photo=photo_file_id,
        caption=caption,
        reply_markup=get_vote_keyboard(0)  # временно, обновим после создания submission
    )
    # Сохраняем в БД
    sub_id = db.create_submission(
        user_id=user.id,
        number=current_number,
        photo_file_id=photo_file_id,
        message_id=sent_msg.message_id
    )
    # Обновляем клавиатуру с реальным submission_id
    await sent_msg.edit_reply_markup(reply_markup=get_vote_keyboard(sub_id))
    # Устанавливаем флаг голосования
    db.set_voting(True)

    # Запускаем фоновую задачу напоминаний, если ещё не запущена
    global reminder_task_started
    if not reminder_task_started:
        reminder_task_started = True
        asyncio.create_task(reminder_loop())

@router.callback_query(F.data.startswith("vote_"))
async def handle_vote(callback: CallbackQuery):
    data = callback.data.split("_")
    action = data[1]  # approve или reject
    submission_id = int(data[2])
    voter_id = callback.from_user.id

    # Проверяем, что голосование активное
    state = db.get_game_state()
    if state is None or not state[2]:  # is_voting
        await callback.answer("Голосование уже завершено или не активно.", show_alert=True)
        return

    # Проверяем, что автор не голосует
    author_id = db.get_submission_author(submission_id)
    if author_id == voter_id:
        await callback.answer("Вы не можете голосовать за своё фото.", show_alert=True)
        return

    # Добавляем голос
    success = db.add_vote(submission_id, voter_id, action)
    if not success:
        await callback.answer("Вы уже проголосовали.", show_alert=True)
        return

    # Получаем информацию о текущем голосовании
    all_votes = db.get_votes_for_submission(submission_id)
    approves = db.count_approves(submission_id)
    rejects = db.count_rejects(submission_id)

    # Определяем активных игроков (кроме автора)
    active_players = db.get_active_players()
    voters = [v[0] for v in all_votes]
    non_voters = [uid for uid in active_players if uid != author_id and uid not in voters]

    # Обновляем сообщение с голосованием (показываем счётчик)
    sub_info = db.cursor.execute("SELECT number, user_id, message_id FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if sub_info:
        number, author_id, msg_id = sub_info
        caption = f"📸 {format_player_name(await callback.bot.get_chat(author_id))} нашёл число {number}.\n"
        caption += f"✅ За: {approves}  ❌ Не за: {rejects}\n"
        if non_voters:
            caption += f"⏳ Ожидают голоса: {len(non_voters)} чел."

        await callback.bot.edit_message_caption(
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            caption=caption,
            reply_markup=get_vote_keyboard(submission_id)
        )

    # Проверяем условия завершения голосования
    # Если есть хотя бы один "Не засчитать" – требуется решение админа
    if rejects > 0:
        # Уведомляем админов
        db.set_admin_decision_needed(True)
        for admin_id in ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"⚖️ Спорное голосование!\n"
                    f"Пользователь {format_player_name(await callback.bot.get_chat(author_id))} нашёл число {number}.\n"
                    f"✅ За: {approves}, ❌ Не за: {rejects}.\n"
                    "Примите решение:",
                    reply_markup=get_admin_decision_keyboard(submission_id)
                )
            except:
                pass
        await callback.answer("Голосование завершено. Решение передано администратору.")
        return

    # Если все активные (кроме автора) проголосовали "Засчитать" – автоматическое принятие
    active_without_author = [uid for uid in active_players if uid != author_id]
    if approves == len(active_without_author) and len(active_without_author) > 0:
        await accept_submission(callback.bot, submission_id)
        return

    await callback.answer("Ваш голос учтён.")

async def accept_submission(bot, submission_id):
    # Получаем данные о заявке
    sub = db.cursor.execute("SELECT user_id, number, message_id FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if not sub:
        return
    user_id, number, msg_id = sub
    db.update_submission_status(submission_id, "accepted")
    db.update_player_score(user_id, number)
    db.set_voting(False)
    db.set_admin_decision_needed(False)

    # Обновляем текущее число
    current_number = number + 1
    db.set_current_number(current_number)

    # Удаляем сообщение с голосованием (чтобы не висело)
    try:
        await bot.delete_message(chat_id=msg_id, message_id=msg_id)
    except:
        pass

    # Отправляем уведомление в группу
    await bot.send_message(
        chat_id=msg_id,  # используем тот же chat_id (группа)
        text=f"🎉 Число {number} выполнено! Игрок {format_player_name(await bot.get_chat(user_id))} получает 1 очко. Следующее число — {current_number}."
    )

    # Удаляем голоса для этой заявки
    db.delete_votes_for_submission(submission_id)

async def reject_submission(bot, submission_id):
    sub = db.cursor.execute("SELECT number, message_id FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if not sub:
        return
    number, msg_id = sub
    db.update_submission_status(submission_id, "rejected")
    db.set_voting(False)
    db.set_admin_decision_needed(False)

    try:
        await bot.delete_message(chat_id=msg_id, message_id=msg_id)
    except:
        pass

    await bot.send_message(
        chat_id=msg_id,
        text=f"❌ Фото не засчитано. Продолжаем искать число {number}."
    )
    db.delete_votes_for_submission(submission_id)

# Обработка решения администратора
@router.callback_query(F.data.startswith("admin_"))
async def handle_admin_decision(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Только администратор может это сделать.", show_alert=True)
        return

    data = callback.data.split("_")
    action = data[1]  # accept или reject
    submission_id = int(data[2])

    if action == "accept":
        await accept_submission(callback.bot, submission_id)
        await callback.answer("Фото засчитано.")
    else:
        await reject_submission(callback.bot, submission_id)
        await callback.answer("Фото отклонено.")

    await callback.message.delete()  # удаляем сообщение админу

# Функция напоминаний (запускается как фоновая задача)
async def reminder_loop():
    from config import REMINDER_INTERVAL_SECONDS, REMINDER_START_AFTER_SECONDS
    while True:
        await asyncio.sleep(60)  # проверяем каждую минуту
        # Проверяем старые pending заявки
        old_subs = db.get_old_pending_submissions(REMINDER_START_AFTER_SECONDS)
        for sub_id, user_id, number, msg_id, created_at in old_subs:
            # Получаем проголосовавших
            voters = db.get_voters_for_submission(sub_id)
            active_players = db.get_active_players()
            author_id = db.get_submission_author(sub_id)
            non_voters = [uid for uid in active_players if uid != author_id and uid not in voters]
            if non_voters:
                # Отправляем напоминание в чат, где было сообщение (msg_id - это ID сообщения в группе)
                try:
                    chat_id = msg_id  # message_id в группе
                    # Получаем имена не проголосовавших
                    names = []
                    for uid in non_voters:
                        user = await callback.bot.get_chat(uid)  # но здесь callback нет. Нужно переделать.
                        # Вместо этого получим из БД username/first_name
                        player = db.cursor.execute("SELECT username, first_name FROM players WHERE user_id=?", (uid,)).fetchone()
                        if player:
                            names.append(player[0] or player[1] or str(uid))
                    if names:
                        await bot.send_message(
                            chat_id,
                            f"⏰ Напоминание о голосовании!\n"
                            f"Следующие участники ещё не проголосовали за число {number}:\n{', '.join(names)}"
                        )
                except Exception as e:
                    print(f"Ошибка отправки напоминания: {e}")
            # Проверяем, не превысило ли время? Нет, мы уже фильтруем старые >1 часа