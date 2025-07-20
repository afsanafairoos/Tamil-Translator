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
        return sum(1 for ac_ in f)

def is_duplicate_translation(original, translated):
    """Check if this exact translation already exists in recent history."""
    try:
        # Check only the latest history file for performance
        current_file = get_latest_history_file()
        if not os.path.exists(current_file):
            return False
        
        original_lower = original.lower().strip()
        translated_lower = translated.lower().strip()
        
        with open(current_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            # Check last 100 entries for duplicates
            rows = list(reader)
            recent_rows = rows[-100:] if len(rows) > 100 else rows
            
            for row in recent_rows:
                if len(row) >= 2:
                    if (row[0].lower().strip() == original_lower and 
                        row[1].lower().strip() == translated_lower):
                        return True
        return False
    except Exception:
        return False

def save_history(original, translated):
    """Save translation history, avoiding exact duplicates."""
    # Skip if it's an exact duplicate
    if is_duplicate_translation(original, translated):
        return
    
    current_file = get_latest_history_file()
    if count_rows_in_file(current_file) >= HISTORY_LIMIT:
        current_file = get_new_history_file()
    
    with open(current_file, "a", newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([original, translated])

def load_history():
    """Load all translation history."""
    rows = []
    for f in get_history_files():
        try:
            with open(f, "r", encoding="utf-8") as file:
                rows.extend(list(csv.reader(file)))
        except Exception:
            continue
    return rows

def get_existing_translation(text):
    """Check if we already have a translation for this text."""
    try:
        # Check recent history first for performance
        current_file = get_latest_history_file()
        if not os.path.exists(current_file):
            return None
        
        text_lower = text.lower().strip()
        
        with open(current_file, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = list(reader)
            # Check last 200 entries
            recent_rows = rows[-200:] if len(rows) > 200 else rows
            
            for row in recent_rows:
                if len(row) >= 2:
                    if row[0].lower().strip() == text_lower:
                        return row[1]  # Return existing translation
        return None
    except Exception:
        return None

def clear_all_history():
    """Clear all translation history files."""
    try:
        for file_path in get_history_files():
            if os.path.exists(file_path):
                os.remove(file_path)
        return True
    except Exception:
        return False

def update_history_entry(old_original, old_translated, new_original, new_translated):
    """Update a specific history entry."""
    try:
        history = load_history()
        updated = False
        
        for i, (orig, trans) in enumerate(history):
            if orig == old_original and trans == old_translated:
                history[i] = (new_original, new_translated)
                updated = True
                break
        
        if updated:
            # Rewrite all history files
            clear_all_history()
            if history:
                current_file = get_latest_history_file()
                with open(current_file, "w", newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    for original, translation in history:
                        writer.writerow([original, translation])
        
        return updated
    except Exception:
        return False

def delete_history_entry(original, translated):
    """Delete a specific history entry."""
    try:
        history = load_history()
        original_length = len(history)
        
        # Remove matching entries
        history = [(orig, trans) for orig, trans in history 
                  if not (orig == original and trans == translated)]
        
        if len(history) < original_length:
            # Rewrite all history files
            clear_all_history()
            if history:
                current_file = get_latest_history_file()
                with open(current_file, "w", newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    for orig, trans in history:
                        writer.writerow([orig, trans])
            return True
        return False
    except Exception:
        return False

def get_history_stats():
    """Get statistics about translation history."""
    try:
        history = load_history()
        total_entries = len(history)
        files_count = len(get_history_files())
        
        # Count unique entries
        unique_entries = len(set(history))
        duplicates = total_entries - unique_entries
        
        return {
            'total_entries': total_entries,
            'unique_entries': unique_entries,
            'duplicates': duplicates,
            'files_count': files_count
        }
    except Exception:
        return {
            'total_entries': 0,
            'unique_entries': 0,
            'duplicates': 0,
            'files_count': 0
        }

def translate_to_tamil(text):
    """Translate text to Tamil, using cache if available."""
    try:
        # First check if we already have this translation
        existing = get_existing_translation(text)
        if existing:
            return existing
        
        # If not found, translate it
        translated = GoogleTranslator(source='auto', target='ta').translate(text)
        if translated.startswith("[Error") or "text length" in translated:
            return None
        
        # Clean up the translation
        if translated:
            translated = translated.strip()
        
        return translated
    except Exception:
        return None
    
