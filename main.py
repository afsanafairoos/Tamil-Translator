import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading, time, keyboard, os, sys

try:
    from translator import translate_to_tamil
    from utils import get_selected_text, is_valid_selection
    from gui import show_translation_popup, show_history_window as history_window
except ImportError as e:
    messagebox.showerror("Import Error", str(e))
    sys.exit(1)

HISTORY_DIR = "history"
HISTORY_FILE = os.path.join(HISTORY_DIR, "translations.txt")
os.makedirs(HISTORY_DIR, exist_ok=True)

def save_line(en, ta):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{en} - {ta}\n")

def load_lines():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        lines = [l.strip() for l in f if " - " in l]
    return [tuple(l.split(" - ", 1)) for l in lines]

class App:
    def __init__(self, root):
        self.root = root
        self.last = ""
        self.running = False
        self._window()
        self._styles()
        self._widgets()
        keyboard.add_hotkey("alt+h", self.show_history)
        self.start()

    def _window(self):
        self.root.title("Tamil‑English Translator")
        self.root.geometry("640x480")
        self.root.configure(bg="#E8E8E8")
        self.root.resizable(True, True)
        self.root.attributes("-topmost", True)
        self.root.update_idletasks()
        w, h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"640x480+{w//2-320}+{h//2-240}")

    def _styles(self):
        s = ttk.Style()
        s.configure("H.TButton", background="#4A4A4A", foreground="black", font=("Arial", 11, "bold"), borderwidth=0)
        s.map("H.TButton", background=[("active", "#5A5A5A")])
        s.configure("Q.TButton", background="#8B0000", foreground="black", font=("Arial", 11, "bold"), borderwidth=0)
        s.map("Q.TButton", background=[("active", "#A50000")])
        s.configure("T.TButton", background="#4CAF50", foreground="black", font=("Arial", 10, "bold"), borderwidth=0)
        s.map("T.TButton", background=[("active", "#45a049")])

    def _widgets(self):
        main = tk.Frame(self.root, bg="#E8E8E8", padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        card = tk.Frame(main, bg="#8B7FB8")
        card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        hdr = tk.Frame(card, bg="#2C2C2C", height=60)
        hdr.pack(fill=tk.X, padx=15, pady=(15, 0))
        hdr.pack_propagate(False)
        c = tk.Canvas(hdr, width=40, height=40, bg="#2C2C2C", highlightthickness=0)
        c.pack(side=tk.LEFT, padx=(20, 10), pady=10)
        c.create_oval(2, 2, 38, 38, fill="#FF6B35", outline="")
        c.create_text(20, 20, text="T", fill="white", font=("Arial", 16, "bold"))
        tk.Label(hdr, text="Tamil‑English Translator", fg="white", bg="#2C2C2C", font=("Arial", 16, "bold")).pack(side=tk.LEFT, pady=15)
        self.status = tk.Label(hdr, text="🟢 Auto‑translate ON", fg="#90EE90", bg="#2C2C2C", font=("Arial", 10))
        self.status.pack(side=tk.RIGHT, padx=(0, 20), pady=15)
        area = tk.Frame(card, bg="#8B7FB8")
        area.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        bar = tk.Frame(area, bg="#2C2C2C", height=30)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="Manual Translation & Recent History", fg="white", bg="#2C2C2C", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)
        box = tk.Frame(area, bg="white", bd=1, relief=tk.FLAT)
        box.pack(fill=tk.BOTH, expand=True)
        inp = tk.Frame(box, bg="white")
        inp.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(inp, text="Enter English text:", bg="white", font=("Arial", 9)).pack(anchor=tk.W)
        self.input = scrolledtext.ScrolledText(inp, height=4, wrap=tk.WORD, font=("Arial", 10), bg="#F8F8F8", bd=1, relief=tk.SOLID)
        self.input.pack(fill=tk.X, pady=(2, 5))
        tk.Button(inp, text="Translate to Tamil", command=self.translate, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), relief=tk.FLAT, bd=0, pady=5).pack()
        hwrap = tk.Frame(box, bg="white")
        hwrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        tk.Label(hwrap, text="Recent translations:", bg="white", font=("Arial", 9)).pack(anchor=tk.W)
        self.history = scrolledtext.ScrolledText(hwrap, height=8, wrap=tk.WORD, font=("Arial", 9), bg="#F0F0F0", bd=1, relief=tk.SOLID, state=tk.DISABLED)
        self.history.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        foot = tk.Frame(card, bg="#8B7FB8")
        foot.pack(fill=tk.X, padx=15, pady=(0, 15))
        self.tgl = ttk.Button(foot, text="Disable Auto‑Translate", style="T.TButton", command=self.toggle)
        self.tgl.pack(side=tk.LEFT, padx=(10, 5), ipadx=15, ipady=8)
        ttk.Button(foot, text="Full History (Alt+H)", style="H.TButton", command=self.show_history).pack(side=tk.LEFT, padx=5, ipadx=15, ipady=8)
        ttk.Button(foot, text="Quit", style="Q.TButton", command=self.quit).pack(side=tk.RIGHT, padx=(0, 10), ipadx=20, ipady=8)

    def start(self):
        self.running = True
        threading.Thread(target=self.loop, daemon=True).start()
        self.update_history()

    def loop(self):
        while self.running:
            time.sleep(1.5)
            try:
                sel = get_selected_text()
            except Exception:
                sel = ""
            inside = self.root.focus_get() is not None
            if sel and sel.strip() and sel != self.last and is_valid_selection(sel) and not inside:
                ta = translate_to_tamil(sel).strip()
                if ta:
                    self.last = sel
                    save_line(sel, ta)
                    self.root.after(0, self.update_history)
                    threading.Thread(target=show_translation_popup, args=(ta,), daemon=True).start()

    def toggle(self):
        if self.running:
            self.running = False
            self.tgl.config(text="Enable Auto‑Translate")
            self.status.config(text="🔴 Auto‑translate OFF", fg="#FFB6C1")
        else:
            self.start()
            self.tgl.config(text="Disable Auto‑Translate")
            self.status.config(text="🟢 Auto‑translate ON", fg="#90EE90")

    def translate(self):
        en = self.input.get("1.0", tk.END).strip()
        if not en or not any(c.isalpha() for c in en):
            messagebox.showwarning("Warning", "Enter valid English text.")
            return
        ta = translate_to_tamil(en).strip()
        if ta:
            save_line(en, ta)
            self.update_history()
            self.input.delete("1.0", tk.END)
            messagebox.showinfo("Translation", f"English: {en}\n\nTamil: {ta}")
        else:
            messagebox.showerror("Error", "Translation failed.")

    def update_history(self):
        data = load_lines()
        self.history.config(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)
        for en, ta in reversed(data[-10:]):
            self.history.insert(tk.END, f"{en} - {ta}\n{'-'*50}\n")
        self.history.config(state=tk.DISABLED)

    def show_history(self):
        history_window(load_lines)

    def quit(self):
        if messagebox.askyesno("Quit", "Are you sure?"):
            self.running = False
            self.root.quit()


def main():
    root = tk.Tk()
    App(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()

if __name__ == "__main__":
    main()
