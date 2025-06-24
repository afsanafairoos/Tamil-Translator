import os
import csv
from datetime import datetime
from deep_translator import GoogleTranslator

HISTORY_FOLDER = "history"
HISTORY_FILE_BASE = "translation_history"
HISTORY_LIMIT = 500

if not os.path.exists(HISTORY_FOLDER):
    os.makedirs(HISTORY_FOLDER)

def get_history_files():
    files = [f for f in os.listdir(HISTORY_FOLDER) if f.startswith(HISTORY_FILE_BASE)]
    files.sort()
    return [os.path.join(HISTORY_FOLDER, f) for f in files]

def get_latest_history_file():
    files = get_history_files()
    if not files:
        return os.path.join(HISTORY_FOLDER, f"{HISTORY_FILE_BASE}_1.csv")
    return files[-1]

def get_new_history_file():
    files = get_history_files()
    new_index = len(files) + 1
    return os.path.join(HISTORY_FOLDER, f"{HISTORY_FILE_BASE}_{new_index}.csv")

def count_rows_in_file(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def save_history(original, translated):
    current_file = get_latest_history_file()
    if count_rows_in_file(current_file) >= HISTORY_LIMIT:
        current_file = get_new_history_file()
    with open(current_file, "a", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([original, translated])

def load_history():
    rows = []
    for f in get_history_files():
        with open(f, "r", encoding="utf-8") as file:
            rows.extend(list(csv.reader(file)))
    return rows

def translate_to_tamil(text):
    try:
        translated = GoogleTranslator(source='auto', target='ta').translate(text)
        if translated.startswith("[Error") or "text length" in translated:
            return None
        return translated
    except:
        return None
