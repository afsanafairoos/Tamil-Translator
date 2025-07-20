import pyperclip
import pyautogui
import time

def get_selected_text():
    """Get the currently selected text by copying it to clipboard."""
    original_clipboard = pyperclip.paste()
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.3)
    selected = pyperclip.paste()
    pyperclip.copy(original_clipboard)
    return selected.strip()

def is_valid_selection(text):
    """Check if the selected text is valid for translation."""
    cleaned = text.strip()
    return (
        cleaned != "" and
        len(cleaned) < 200 and
        any(c.isalpha() for c in cleaned)
    )