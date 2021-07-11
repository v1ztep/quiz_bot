import json
import logging
import os
from enum import Enum
from functools import partial
from random import choice

import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from connect_to_redis_db import connect_to_redis_db
from logs_handler import TelegramLogsHandler

logger = logging.getLogger('quiz_bots logger')
STATES = Enum('state', 'NEW_QUESTION, ANSWER')


def start(bot, update, db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    update.message.reply_text('Чатбот ЧГК активирован!',
                              reply_markup=reply_markup)
    if not db.get(f'{user_id}_score'):
        db.set(f'{user_id}_score', 0)
    return STATES.NEW_QUESTION


def new_question(bot, update, quiz_questions, db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    random_question = choice(list(quiz_questions))
    update.message.reply_text(random_question, reply_markup=reply_markup)
    db.set(user_id, random_question)
    return STATES.ANSWER


def capitulate(bot, update, quiz_questions, db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    question = db.get(user_id)
    update.message.reply_text(quiz_questions[question],
                              reply_markup=reply_markup)
    return STATES.NEW_QUESTION


def check_answer(bot, update, quiz_questions, db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    user_answer = update.message.text
    question = db.get(user_id)
    right_answer = quiz_questions[question]
    if user_answer.lower() == right_answer.split('(')[0].split('.')[0].lower().strip():
        points = db.get(f'{user_id}_score')
        db.set(f'{user_id}_score', int(points) + 1)
        update.message.reply_text('Правильно! Поздравляю!',
                                  reply_markup=reply_markup)
    else:
        update.message.reply_text(f'Правильный ответ был: {right_answer}\n'
                                  f'Попробуешь ещё раз?',
                                  reply_markup=reply_markup)
    return STATES.NEW_QUESTION


def score(bot, update, db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    points = db.get(f'{user_id}_score')
    update.message.reply_text(points, reply_markup=reply_markup)
    return STATES.NEW_QUESTION


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ТГ бот запущен')
    db = connect_to_redis_db()

    with open('quiz_questions.json', 'r', encoding='utf8') as file:
        quiz_questions = json.loads(file.read())

    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счёт']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)

    updater = Updater(tg_token)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(
            'start',
            partial(start, reply_markup=reply_markup, db=db)
        )],

        states={
            STATES.NEW_QUESTION: [
                MessageHandler(
                    Filters.regex('^Новый вопрос$'),
                    partial(new_question,
                            quiz_questions=quiz_questions,
                            db=db,
                            reply_markup=reply_markup)
                )
            ],
            STATES.ANSWER: [
                MessageHandler(
                    Filters.regex('^Сдаться$'),
                    partial(capitulate,
                            quiz_questions=quiz_questions,
                            db=db,
                            reply_markup=reply_markup)
                ),
                MessageHandler(
                    Filters.text,
                    partial(check_answer,
                            quiz_questions=quiz_questions,
                            db=db,
                            reply_markup=reply_markup)
                ),
            ],
        },
        fallbacks=[
            MessageHandler(
                Filters.regex('^Мой счёт$'),
                partial(score, db=db, reply_markup=reply_markup)
            )
        ]
    )
    dp.add_handler(conv_handler)

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
