import tkinter as tk
from tkinter import messagebox
import pyautogui

PINK_BG = "#ffe6f0"
PINK_LIGHT = "#fff0f5"
BUTTON_PINK = "#ffb6c1"
BUTTON_PINK_DARK = "#fcb5c0"

def show_translation_popup(translated_text):
    popup = tk.Tk()
    popup.overrideredirect(True)
    popup.attributes('-topmost', True)
    popup.configure(bg=PINK_BG)
    x, y = pyautogui.position()
    popup.geometry(f"+{x + 20}+{y + 20}")
    label = tk.Label(popup, text=translated_text, font=("Arial", 11), bg=PINK_BG, wraplength=300, justify='left')
    label.pack(padx=10, pady=10)
    popup.after(4000, popup.destroy)
    popup.mainloop()

def show_history_window(load_history_func):
    history = load_history_func()
    if not history:
        messagebox.showinfo("No History", "No history available.")
        return

    win = tk.Tk()
    win.title("Translation History")
    win.geometry("600x400")
    win.configure(bg=PINK_BG)

    text_area = tk.Text(win, wrap="word", font=("Arial", 10), bg=PINK_LIGHT)
    for row in history[-200:]:
        if len(row) != 2:
            continue
        original, translated = row
        entry = f"EN: {original}\nTA: {translated}\n{'-'*50}\n"
        text_area.insert(tk.END, entry)
    text_area.pack(fill="both", expand=True, padx=10, pady=10)

    def confirm_and_clear():
        if messagebox.askyesno("Confirm", "Do you really want to delete all history?"):
            from translator import get_history_files
            import os
            for f in get_history_files():
                os.remove(f)
            messagebox.showinfo("Deleted", "All history deleted successfully.")
            win.destroy()

    clear_btn = tk.Button(win, text="Clear All History", command=confirm_and_clear, bg=BUTTON_PINK)
    clear_btn.pack(pady=5)
    win.mainloop()

def launch_app_window(get_last_n_history_func, show_history_func, quit_callback):
    root = tk.Tk()
    root.title("Tamil Translator App")
    root.geometry("400x300")
    root.configure(bg=PINK_BG)
    root.attributes('-topmost', True)

    label = tk.Label(root, text=" Tamil Translator is Running", font=("Arial", 12), bg=PINK_BG)
    label.pack(pady=10)

    history_box = tk.Text(root, height=10, font=("Arial", 9), wrap="word", bg=PINK_LIGHT)
    last_history = get_last_n_history_func(5)
    for row in last_history:
        if len(row) != 2:
            continue
        original, translated = row
        history_box.insert(tk.END, f"EN: {original}\nTA: {translated}\n{'-'*50}\n")
    history_box.config(state='disabled')
    history_box.pack(padx=10, pady=5, fill="both", expand=True)

    history_btn = tk.Button(root, text="View Full History", command=show_history_func, bg=BUTTON_PINK)
    history_btn.pack(pady=5)

    quit_btn = tk.Button(root, text="Quit", command=quit_callback, bg=BUTTON_PINK_DARK)
    quit_btn.pack(pady=5)

    return root
