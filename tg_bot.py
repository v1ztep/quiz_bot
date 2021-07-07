import json
import logging
import os
from enum import Enum
from functools import partial
from random import choice

import redis
import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import ConversationHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logs_handler import TelegramLogsHandler

logger = logging.getLogger('chatbots logger')
states = Enum('state', 'NEW_QUESTION, ANSWER')


def start(bot, update, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    update.message.reply_text('Чатбот ЧГК активирован!',
                              reply_markup=reply_markup)
    if not redis_db.get(f'{user_id}_score'):
        redis_db.set(f'{user_id}_score', 0)
    return states.NEW_QUESTION


def new_question(bot, update, quiz_questions, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    random_question = choice(list(quiz_questions))
    update.message.reply_text(random_question, reply_markup=reply_markup)
    redis_db.set(user_id, random_question)
    return states.ANSWER


def capitulate(bot, update, quiz_questions, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    question = redis_db.get(user_id)
    update.message.reply_text(quiz_questions[question],
                              reply_markup=reply_markup)
    return states.NEW_QUESTION


def check_answer(bot, update, quiz_questions, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    user_answer = update.message.text
    question = redis_db.get(user_id)
    right_answer = quiz_questions[question]
    if user_answer.lower() == right_answer.split('(')[0].split('.')[0].lower().strip():
        points = redis_db.get(f'{user_id}_score')
        redis_db.set(f'{user_id}_score', int(points) + 1)
        update.message.reply_text('Правильно! Поздравляю!',
                                  reply_markup=reply_markup)
    else:
        update.message.reply_text(f'Правильный ответ был: {right_answer}\n'
                                  f'Попробуешь ещё раз?',
                                  reply_markup=reply_markup)
    return states.NEW_QUESTION


def score(bot, update, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    points = redis_db.get(f'{user_id}_score')
    update.message.reply_text(points, reply_markup=reply_markup)
    return states.NEW_QUESTION


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
    redis_db_pass = os.getenv('REDIS_DB_PASS')
    redis_db = redis.Redis(host=redis_host,
                           port=redis_port,
                           db=0,
                           password=redis_db_pass,
                           decode_responses=True)
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ТГ бот запущен')

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
            partial(start, reply_markup=reply_markup, redis_db=redis_db)
        )],

        states={
            states.NEW_QUESTION: [
                MessageHandler(
                    Filters.regex('^Новый вопрос$'),
                    partial(new_question,
                            quiz_questions=quiz_questions,
                            redis_db=redis_db,
                            reply_markup=reply_markup)
                )
            ],
            states.ANSWER: [
                MessageHandler(
                    Filters.regex('^Сдаться$'),
                    partial(capitulate,
                            quiz_questions=quiz_questions,
                            redis_db=redis_db,
                            reply_markup=reply_markup)
                ),
                MessageHandler(
                    Filters.text,
                    partial(check_answer,
                            quiz_questions=quiz_questions,
                            redis_db=redis_db,
                            reply_markup=reply_markup)
                ),
            ],
        },
        fallbacks=[
            MessageHandler(
                Filters.regex('^Мой счёт$'),
                partial(score, redis_db=redis_db, reply_markup=reply_markup)
            )
        ]
    )
    dp.add_handler(conv_handler)

    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
