import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import keyboard
import sys

try:

    from translator import translate_to_tamil, save_history, load_history
    from utils import get_selected_text, is_valid_selection
    from gui import show_translation_popup, show_history_window as history_window
except ImportError as exc:
    messagebox.showerror("Import Error", str(exc))
    sys.exit(1)


class App:
    """Main application window"""

    START_W = 380
    START_H = 460

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.last_selection: str = ""
        self.running = False

        self._window()
        self._styles()
        self._widgets()

        keyboard.add_hotkey("alt+h", self.show_history)
        self.start()

    def _window(self) -> None:
        self.root.title("Tamil‑English Translator")
        self.root.geometry(f"{self.START_W}x{self.START_H}")
        self.root.resizable(True, True)
        self.root.minsize(self.START_W, self.START_H)
        self.root.attributes("-topmost", True)

        # center once at start
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(
            f"{self.START_W}x{self.START_H}+{sw//2-self.START_W//2}+{sh//2-self.START_H//2}"
        )

    def _styles(self) -> None:
        s = ttk.Style()
        s.configure("H.TButton", background="#4A4A4A", foreground="black", font=("Arial", 9, "bold"), borderwidth=0)
        s.map("H.TButton", background=[("active", "#5A5A5A")])
        s.configure("Q.TButton", background="#8B0000", foreground="black", font=("Arial", 9, "bold"), borderwidth=0)
        s.map("Q.TButton", background=[("active", "#A50000")])
        s.configure("T.TButton", background="#4CAF50", foreground="black", font=("Arial", 8, "bold"), borderwidth=0)
        s.map("T.TButton", background=[("active", "#45a049")])

    def _widgets(self) -> None:
        main = tk.Frame(self.root, bg="#E8E8E8", padx=12, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(main, bg="#8B7FB8")
        card.pack(fill=tk.BOTH, expand=True)

        # Header
        hdr = tk.Frame(card, bg="#2C2C2C", height=50)
        hdr.pack(fill=tk.X, padx=10, pady=(10, 0))
        hdr.pack_propagate(False)

        icon = tk.Canvas(hdr, width=28, height=28, bg="#2C2C2C", highlightthickness=0)
        icon.pack(side=tk.LEFT, padx=(14, 6), pady=8)
        icon.create_oval(2, 2, 26, 26, fill="#FF6B35", outline="")
        icon.create_text(14, 14, text="T", fill="white", font=("Arial", 12, "bold"))

        tk.Label(
            hdr,
            text="Tamil‑English Translator",
            fg="white",
            bg="#2C2C2C",
            font=("Arial", 12, "bold"),
        ).pack(side=tk.LEFT, pady=12)

        self.status_lbl = tk.Label(
            hdr,
            text="🟢",
            fg="#90EE90",
            bg="#2C2C2C",
            font=("Arial", 8),
        )
        self.status_lbl.pack(side=tk.RIGHT, padx=(0, 12), pady=12)

        # Body
        area = tk.Frame(card, bg="#8B7FB8")
        area.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        bar = tk.Frame(area, bg="#2C2C2C", height=24)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Label(bar, text="Manual Translation & History", fg="white", bg="#2C2C2C", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=6)

        box = tk.Frame(area, bg="white", bd=1, relief=tk.FLAT)
        box.pack(fill=tk.BOTH, expand=True)

        inp = tk.Frame(box, bg="white")
        inp.pack(fill=tk.X, padx=6, pady=3)
        tk.Label(inp, text="Enter English:", bg="white", font=("Arial", 7)).pack(anchor=tk.W)

        self.input_txt = scrolledtext.ScrolledText(inp, height=3, wrap=tk.WORD, font=("Arial", 8), bg="#F8F8F8", bd=1, relief=tk.SOLID)
        self.input_txt.pack(fill=tk.X, pady=(2, 3))

        tk.Button(inp, text="Translate", command=self._manual_translate, bg="#4CAF50", fg="white", font=("Arial", 8, "bold"), relief=tk.FLAT, bd=0, pady=3).pack()

        hwrap = tk.Frame(box, bg="white")
        hwrap.pack(fill=tk.BOTH, expand=True, padx=6, pady=3)
        tk.Label(hwrap, text="Recent:", bg="white", font=("Arial", 7)).pack(anchor=tk.W)

        self.history_txt = scrolledtext.ScrolledText(hwrap, height=5, wrap=tk.WORD, font=("Arial", 7), bg="#F0F0F0", bd=1, relief=tk.SOLID, state=tk.DISABLED)
        self.history_txt.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Footer
        foot = tk.Frame(card, bg="#8B7FB8")
        foot.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.toggle_btn = ttk.Button(foot, text="Disable Auto", style="T.TButton", command=self._toggle_auto)
        self.toggle_btn.pack(side=tk.LEFT, padx=(6, 3), ipadx=8, ipady=4)

        ttk.Button(foot, text="History (Alt+H)", style="H.TButton", command=self.show_history).pack(side=tk.LEFT, padx=3, ipadx=8, ipady=4)

        ttk.Button(foot, text="Quit", style="Q.TButton", command=self._quit).pack(side=tk.RIGHT, padx=(0, 6), ipadx=10, ipady=4)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._auto_loop, daemon=True).start()
        self._refresh_history()

    def _auto_loop(self) -> None:
        while self.running:
            time.sleep(1.5)
            try:
                sel = get_selected_text()
            except Exception:
                sel = ""
            if sel and sel.strip() and sel != self.last_selection and is_valid_selection(sel) and self.root.focus_get() is None:
                ta = translate_to_tamil(sel)
                if ta:
                    self.last_selection = sel
                    save_history(sel, ta)
                    self.root.after(0, self._refresh_history)
                    threading.Thread(target=show_translation_popup, args=(ta,), daemon=True).start()

    def _toggle_auto(self) -> None:
        if self.running:
            # 🔴 Turn OFF
            self.running = False
            self.toggle_btn.config(text="Enable Auto")
            self.status_lbl.config(text="🔴", fg="#FFB6C1")
        else:
            # 🟢 Turn ON
            self.toggle_btn.config(text="Disable Auto")
            self.status_lbl.config(text="🟢", fg="#90EE90")
            self.start()  # start() sets self.running = True and spins the thread

    def _manual_translate(self) -> None:
        en = self.input_txt.get("1.0", tk.END).strip()
        if not en or not any(c.isalpha() for c in en):
            messagebox.showwarning("Warning", "Enter valid English text.")
            return
        ta = translate_to_tamil(en)
        if ta:
            save_history(en, ta)
            self._refresh_history()
            self.input_txt.delete("1.0", tk.END)
            messagebox.showinfo("Translation", f"English:\n{en}\n\nTamil:\n{ta}")
        else:
            messagebox.showerror("Error", "Translation failed.")

    def _refresh_history(self) -> None:
        records = load_history()
        self.history_txt.config(state=tk.NORMAL)
        self.history_txt.delete("1.0", tk.END)
        for en, ta in reversed(records[-10:]):
            self.history_txt.insert(tk.END, f"{en} - {ta}\n{'-' * 40}\n")
        self.history_txt.config(state=tk.DISABLED)

    def show_history(self) -> None:
        history_window(load_history)

    def _quit(self) -> None:
        if messagebox.askyesno("Quit", "Are you sure?"):
            self.running = False
            self.root.quit()

def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app._quit)
    root.mainloop()


if __name__ == "__main__":
    main()
