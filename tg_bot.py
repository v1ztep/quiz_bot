import html
import json
import logging
import os
import textwrap
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
from telegram.ext import Updater

from check_similarity import check_similarity
from get_questions import get_quiz_questions
from logs_handler import TelegramLogsHandler
from redis_persistence import RedisPersistence

logger = logging.getLogger('quiz_bots logger')
NEW_QUESTION, ANSWER = range(2)

custom_keyboard = [['Новый вопрос', 'Сдаться'],
                   ['Мой счёт']]
REPLY_MARKUP = telegram.ReplyKeyboardMarkup(custom_keyboard,
                                            resize_keyboard=True)


def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Чатбот ЧГК активирован!',
                              reply_markup=REPLY_MARKUP)
    context.user_data['user_score'] = 0
    if not context.bot_data:
        context.bot_data['questions'] = get_quiz_questions()
    return NEW_QUESTION


def new_question(update: Update, context: CallbackContext) -> int:
    random_question = choice(list(context.bot_data['questions']))
    update.message.reply_text(random_question, reply_markup=REPLY_MARKUP)
    context.user_data['user_question'] = random_question
    return ANSWER


def capitulate(update: Update, context: CallbackContext) -> int:
    question = context.user_data['user_question']
    update.message.reply_text(context.bot_data['questions'][question],
                              reply_markup=REPLY_MARKUP)
    return NEW_QUESTION


def check_answer(update: Update, context: CallbackContext) -> int:
    user_answer = update.message.text
    question = context.user_data['user_question']
    right_answer = context.bot_data['questions'][question]
    if check_similarity(user_answer, right_answer):
        context.user_data['user_score'] += 1
        update.message.reply_text('Правильно! Поздравляю!',
                                  reply_markup=REPLY_MARKUP)
    else:
        update.message.reply_text(f'Правильный ответ был: {right_answer}\n'
                                  f'Попробуешь ещё раз?',
                                  reply_markup=REPLY_MARKUP)
    return NEW_QUESTION


def get_score(update: Update, context: CallbackContext) -> int:
    points = context.user_data['user_score']
    update.message.reply_text(points, reply_markup=REPLY_MARKUP)
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
    logger.exception(msg='Exception while handling an update:')

    tb_list = traceback.format_exception(None, context.error,
                                         context.error.__traceback__)
    tb_string = ''.join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'''An exception was raised while handling an update
        <pre>update = {html.escape(json.dumps(
            update_str, indent=2, ensure_ascii=False))}</pre>
        <pre>context.user_data = {html.escape(str(context.user_data))}</pre>
        <pre>{html.escape(tb_string)}</pre>'''
    )
    context.bot.send_message(chat_id=tg_chat_id, text=textwrap.dedent(message),
                             parse_mode=ParseMode.HTML)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ТГ бот запущен')

    redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
    redis_db_pass = os.getenv('REDIS_DB_PASS')
    persistence = RedisPersistence(
        host=redis_host,
        port=redis_port,
        db=0,
        password=redis_db_pass
    )
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
                MessageHandler(Filters.regex('^Мой счёт$'), get_score),
                MessageHandler(Filters.text, check_answer)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex('^Мой счёт$'), get_score)],
        name="my_conversation",
        persistent=True,
    )
    dp.add_handler(conv_handler)

    dp.add_error_handler(partial(error_handler, tg_chat_id=tg_chat_id))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
