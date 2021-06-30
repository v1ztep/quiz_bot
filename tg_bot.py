import json
import logging
import os
from functools import partial
from random import choice

import redis
import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logs_handler import TelegramLogsHandler

logger = logging.getLogger('chatbots logger')


def start(bot, update, reply_markup):
    update.message.reply_text('Чатбот для викторин активирован!')
    update.message.reply_text(reply_markup=reply_markup)


def reply(bot, update, quiz_questions, redis_db, reply_markup):
    user_id = f'tg{update.message.chat_id}'
    user_answer = update.message.text
    question = redis_db.get(user_id)
    if user_answer == 'Новый вопрос':
        random_question = choice(list(quiz_questions))
        update.message.reply_text(random_question, reply_markup=reply_markup)
        redis_db.set(user_id, random_question)
    elif user_answer == 'Сдаться':
        update.message.reply_text(quiz_questions[question],
                                  reply_markup=reply_markup)
    elif user_answer.lower() == quiz_questions[question].split('.')[0].lower():
        update.message.reply_text('Правильно! Поздравляю!',
                                  reply_markup=reply_markup)
    else:
        update.message.reply_text('Неправильно… Попробуешь ещё раз?',
                                  reply_markup=reply_markup)


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
    dp.add_handler(
        CommandHandler(
            'start',
            partial(start, reply_markup=reply_markup)
        )
    )
    dp.add_handler(
        MessageHandler(
            Filters.text,
            partial(reply,
                    quiz_questions=quiz_questions,
                    redis_db=redis_db,
                    reply_markup=reply_markup)
        )
    )
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
