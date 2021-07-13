import json
import logging
import os
import random
from connect_to_redis_db import connect_to_redis_db
import telegram
import vk_api as vk
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.keyboard import VkKeyboardColor
from vk_api.longpoll import VkEventType
from vk_api.longpoll import VkLongPoll
from vk_api.utils import get_random_id

from logs_handler import TelegramLogsHandler

logger = logging.getLogger('quiz_bots logger')


def create_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def new_question(event, vk_api, quiz_questions, db):
    user_id = f'vk{event.user_id}'
    random_question = random.choice(list(quiz_questions))
    db.set(user_id, random_question)
    send_message(event, vk_api, random_question)


def capitulate(event, vk_api, quiz_questions, db):
    user_id = f'vk{event.user_id}'
    question = db.get(user_id)
    send_message(event, vk_api, quiz_questions[question])


def score(event, vk_api, db):
    user_id = f'vk{event.user_id}'
    points = get_player_score(user_id, db)
    send_message(event, vk_api, points)


def get_player_score(user_id, db):
    points = db.get(f'{user_id}_score')
    if not points:
        db.set(f'{user_id}_score', 0)
        points = 0
    return points


def check_answer(event, vk_api, quiz_questions, db):
    user_id = f'vk{event.user_id}'
    user_answer = event.text
    question = db.get(user_id)
    if not question:
        return
    right_answer = quiz_questions[question]
    if user_answer.lower() == right_answer.split('(')[0].split('.')[0].lower().strip():
        points = get_player_score(user_id, db)
        db.set(f'{user_id}_score', int(points) + 1)
        send_message(event, vk_api, 'Правильно! Поздравляю!')
    else:
        send_message(event, vk_api, f'Правильный ответ был: {right_answer}\n'
                                    f'Попробуешь ещё раз?')


def send_message(event, vk_api, message):
    vk_api.messages.send(
        user_id=event.user_id,
        message=message,
        random_id=get_random_id(),
        keyboard=create_keyboard()
    )


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=tg_token)
    vk_token = os.getenv('VK_BOT_TOKEN')
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ВК бот запущен')
    db = connect_to_redis_db()

    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)
    with open('quiz_questions.json', 'r', encoding='utf8') as file:
        quiz_questions = json.loads(file.read())

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text == 'Новый вопрос':
                new_question(event, vk_api, quiz_questions, db)
            elif event.text == 'Сдаться':
                capitulate(event, vk_api, quiz_questions, db)
                new_question(event, vk_api, quiz_questions, db)
            elif event.text == 'Мой счёт':
                score(event, vk_api, db)
            else:
                check_answer(event, vk_api, quiz_questions, db)
                new_question(event, vk_api, quiz_questions, db)


if __name__ == "__main__":
    main()
