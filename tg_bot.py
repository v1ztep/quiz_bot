import html
import json
import logging
import os
import traceback
from functools import partial
from random import choice

import telegram
from dotenv import load_dotenv
from telegram import ParseMode
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import PicklePersistence
from telegram.ext import Updater
from get_questions import get_quiz_questions

from connect_to_redis_db import connect_to_redis_db
from logs_handler import TelegramLogsHandler

logger = logging.getLogger('quiz_bots logger')
NEW_QUESTION, ANSWER = range(2)

custom_keyboard = [['Новый вопрос', 'Сдаться'],
                   ['Мой счёт']]
reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)

quiz_questions = get_quiz_questions()
db = connect_to_redis_db()


def start(update: Update, context: CallbackContext) -> int:
    db_user_id = f'tg{update.effective_user.id}'
    db_user_score = f'{db_user_id}_score'
    context.user_data['db_user_id'] = db_user_id
    context.user_data['db_user_score'] = db_user_score
    update.message.reply_text('Чатбот ЧГК активирован!',
                              reply_markup=reply_markup)
    if not db.get(db_user_score):
        db.set(db_user_score, 0)
    return NEW_QUESTION


def new_question(update: Update, context: CallbackContext) -> int:
    random_question = choice(list(quiz_questions))
    update.message.reply_text(random_question, reply_markup=reply_markup)
    db.set(context.user_data['db_user_id'], random_question)
    return ANSWER


def capitulate(update: Update, context: CallbackContext) -> int:
    question = db.get(context.user_data['db_user_id'])
    update.message.reply_text(quiz_questions[question],
                              reply_markup=reply_markup)
    return NEW_QUESTION


def check_answer(update: Update, context: CallbackContext) -> int:
    user_answer = update.message.text
    question = db.get(context.user_data['db_user_id'])
    right_answer = quiz_questions[question]
    if user_answer.lower() == right_answer.split('(')[0].split('.')[0].lower().strip():
        points = db.get(context.user_data['db_user_score'])
        db.set(context.user_data['db_user_score'], int(points) + 1)
        update.message.reply_text('Правильно! Поздравляю!',
                                  reply_markup=reply_markup)
    else:
        update.message.reply_text(f'Правильный ответ был: {right_answer}\n'
                                  f'Попробуешь ещё раз?',
                                  reply_markup=reply_markup)
    return NEW_QUESTION


def score(update: Update, context: CallbackContext) -> int:
    points = db.get(context.user_data['db_user_score'])
    update.message.reply_text(points, reply_markup=reply_markup)
    user_id = update.effective_user.id
    user_state = get_user_state(context, user_id)
    return user_state


def get_user_state(context: CallbackContext, user_id: int) -> int:
    persistence = context.dispatcher.persistence
    conversations = persistence.get_conversations('my_conversation')
    for conversation, user_state in conversations.items():
        if user_id in conversation:
            return user_state


def error_handler(update: object, context: CallbackContext, tg_chat_id: int) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )
    context.bot.send_message(chat_id=tg_chat_id, text=message, parse_mode=ParseMode.HTML)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ТГ бот запущен')

    persistence = PicklePersistence(filename='conversationbot')
    updater = Updater(tg_token, persistence=persistence)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NEW_QUESTION: [
                MessageHandler(Filters.regex('^Новый вопрос$'), new_question)
            ],
            ANSWER: [
                MessageHandler(Filters.regex('^Новый вопрос$'), new_question),
                MessageHandler(Filters.regex('^Сдаться$'), capitulate),
                MessageHandler(Filters.regex('^Мой счёт$'), score),
                MessageHandler(Filters.text, check_answer)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Мой счёт$'), score)],
        name="my_conversation",
        persistent=True,
    )
    dp.add_handler(conv_handler)

    dp.add_error_handler(partial(error_handler, tg_chat_id=tg_chat_id))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
