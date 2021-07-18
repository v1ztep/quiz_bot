from fuzzywuzzy import fuzz


def check_similarity(user_answer, right_answer):
    similarity_check = fuzz.WRatio(
        user_answer.lower().strip(),
        # Для сверки оставляю ответ без пояснений - идущих после скобки\точки.
        right_answer.split('(')[0].split('.')[0].lower().strip()
    )
    return similarity_check >= 80
