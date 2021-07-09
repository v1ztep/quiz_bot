import json
import re
from pathlib import Path


def get_quiz_questions(filepath):
    with open(filepath, "r", encoding='KOI8-R') as file:
        file_contents = file.read()
    contents_parts = file_contents.split('\n\n')

    questions = []
    answers = []
    for text in contents_parts:
        if 'Вопрос' in text and text.split()[1].replace(':', '').isdigit():
            questions.append(clear_text(text))
        elif 'Ответ:' in text:
            answers.append(clear_text(text))

    quiz_questions = dict(zip(questions, answers))
    return quiz_questions


def clear_text(text):
    return ' '.join(text.split(':\n')[1::]).\
        replace('\n', ' ').\
        replace('"', '').\
        replace('...','').\
        strip()


def del_trash(questions_with_trash):
    out_of_trash_questions = {}
    for question, answer in questions_with_trash.items():
        question_without_remark = re.sub(r'\[.*\]', '', question)
        answer_without_remark = re.sub(r'\[.*\]', '', answer)
        if '(pic:' in question or '(pic:' in answer or '<раздатка>' in question \
                or '.jpg' in question or '.jpg' in answer:
            continue
        elif 'Блиц' in question_without_remark:
            blitz_questions = split_blitz(question_without_remark, answer_without_remark)
            out_of_trash_questions.update(blitz_questions)
        else:
            out_of_trash_questions[question_without_remark] = answer_without_remark
    return out_of_trash_questions


def split_blitz(questions, answers):
    digits_with_dot_re = r'\b\d{1,2}\b\.'
    only_blitz_questions = questions.split('Блиц')[1].strip()
    entry = list(map(str.strip, re.split(digits_with_dot_re, only_blitz_questions)[:1]))[0]

    split_questions = list(map(str.strip, re.split(digits_with_dot_re, only_blitz_questions)[1:]))
    split_answers = list(map(str.strip, re.split(digits_with_dot_re, answers)[1:]))
    questions_difference = len(split_questions) != len(split_answers)
    if questions_difference or not split_questions:
        return {}
    if entry:
        entry_questions = [entry + question for question in split_questions]
        blitz_questions = dict(zip(entry_questions, split_answers))
    else:
        blitz_questions = dict(zip(split_questions, split_answers))
    return blitz_questions


def main():
    questions_paths = Path('quiz-questions/').glob('*.txt')

    questions = {}
    for questions_path in questions_paths:
        new_questions = get_quiz_questions(questions_path)
        questions.update(new_questions)

    out_of_trash_questions = del_trash(questions)

    with open('quiz_questions.json', 'w', encoding='utf8') as file:
        json.dump(out_of_trash_questions, file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
