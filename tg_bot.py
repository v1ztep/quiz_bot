import json
import logging
import os
from functools import partial
from random import choice

import telegram
from dotenv import load_dotenv
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logs_handler import TelegramLogsHandler

logger = logging.getLogger('chatbots logger')


def start(bot, update, custom_keyboard):
    update.message.reply_text('Чатбот для викторин активирован!')
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    update.message.reply_text(reply_markup=reply_markup)


def reply(bot, update, quiz_questions):
    if update.message.text == 'Новый вопрос':
        random_question = choice(list(quiz_questions))
        update.message.reply_text(random_question)
    else:
        update.message.reply_text(update.message.text)


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

    with open('quiz_questions.json', 'r', encoding='utf8') as file:
        quiz_questions = json.loads(file.read())

    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счёт']]
    updater = Updater(tg_token)
    dp = updater.dispatcher
    dp.add_handler(
        CommandHandler(
            'start',
            partial(start, custom_keyboard=custom_keyboard)
        )
    )
    dp.add_handler(
        MessageHandler(
            Filters.text,
            partial(reply, quiz_questions=quiz_questions)
        )
    )
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
