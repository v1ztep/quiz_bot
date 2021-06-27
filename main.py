import json
from pathlib import Path


def get_quiz_questions(filepath):
    with open(filepath, "r", encoding='KOI8-R') as file:
        file_contents = file.read()
    contents_parts = file_contents.split('\n\n')

    questions = []
    answers = []
    for text in contents_parts:
        if 'Вопрос' in text:
            if text.split()[1].replace(':','').isdigit():
                questions.append(clear_text(text))
        elif 'Ответ:' in text:
            answers.append(clear_text(text))

    quiz_questions = dict(zip(questions, answers))
    return quiz_questions


def clear_text(text):
    return ' '.join(text.split(':\n')[1::]).replace('\n',' ')


def main():
    questions_paths = Path('quiz-questions/').glob('*.txt')

    questions = {}
    for questions_path in questions_paths:
        new_questions = get_quiz_questions(questions_path)
        questions.update(new_questions)

    with open('quiz_questions.json', 'w', encoding='utf8') as file:
        json.dump(questions, file, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    main()
