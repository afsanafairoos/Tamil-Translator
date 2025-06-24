import threading
import time
import keyboard

from translator import translate_to_tamil, save_history, load_history
from utils import get_selected_text, is_valid_selection
from gui import show_translation_popup, show_history_window, launch_app_window

last_text = ""

def auto_translate_loop():
    global last_text
    while True:
        time.sleep(1.5)
        try:
            selected_text = get_selected_text()
            if selected_text and selected_text != last_text and is_valid_selection(selected_text):
                translated = translate_to_tamil(selected_text)
                if translated:
                    last_text = selected_text
                    save_history(selected_text, translated)
                    threading.Thread(target=show_translation_popup, args=(translated,), daemon=True).start()
        except:
            continue

def main():
    root = launch_app_window(
        get_last_n_history_func=lambda n: load_history()[-n:],
        show_history_func=show_history_window,
        quit_callback=lambda: root.destroy()
    )
    # Start background translation thread after GUI loads
    root.after(100, lambda: threading.Thread(target=auto_translate_loop, daemon=True).start())
    root.mainloop()

if __name__ == "__main__":
    print("✅ Tamil Translator running...")
    print("💡 Auto translation is live")
    print("📘 Press Alt + H to view full history")
    keyboard.add_hotkey('alt+h', lambda: show_history_window())
    main()
