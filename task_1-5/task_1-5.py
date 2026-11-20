#Для проверки заданий уберите лишние комментарии и запустите код в терминале. Вводите данные по запросу программы.

#Задание 1. Сделал так чтобы пользователь мог сам ввести текст и максимальную длину строки
"""
def format_text(text, max_length):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + len(word) + 1 <= max_length:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


text = input("Введите текст: ")

print(format_text(text, 70))
"""
#########################################################################################################################################################################

#Задание 2. Также сделал возможность пользователю самому ввести номер билета и количество цифр в нём
"""
from itertools import combinations

def is_lucky_ticket(count, digits):
    if len(digits) != count:
        print("Количество цифр в билете не соответствует введенной длине.")
        return False

    total = sum(digits)

    if total % 2 != 0:
        print("Сумма цифр нечетная, счастливого билета не существует.")
        return False

    target = total // 2

    for group in combinations(digits, count // 2):
        if sum(group) == target:
            return True

    return False


print(is_lucky_ticket(int(input("Введите длину билета: ")), list(map(int, input("Введите номер билета (Ваше количество цифр через пробел): ").split(' ')))))
"""
##########################################################################################################################################################################

#Задание 3. 
"""
data = {
    "a": {
        "b": {
            "c": "+++"
        }
    }
}


def get_nested_value(data, path):
    result = data

    try:
        for key in path.split("."):
            result = result[key]
        return result
    except (KeyError, TypeError):
        return None


print(get_nested_value(data, "a.b.c"))
"""
###########################################################################################################################################################################

#Задание 4. Сделал задание с помощью импорта библиотеки json
"""
import json

inData = '{"one": ["http", "yandex.ru"], "two": ["https", "google.com"]}'

outData = json.loads(inData)

print(outData)
"""
############################################################################################################################################################################

#Задание 5.
""""""
import pandas as pd

d1 = {
    'a': [1, 2, 3],
    'b': [None, 5, 6],
    'c': [7, None, 9]
}

d2 = {
    'b': [4, 89, 87],
    'c': [54, 8, 35],
    'd': [10, 11, 12]
}

df1 = pd.DataFrame(d1)
df2 = pd.DataFrame(d2)

df3 = df1.fillna(df2).astype(int)

print(df3)
