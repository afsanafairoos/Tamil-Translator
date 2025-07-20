import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import keyboard
import sys
import csv
import os

try:
    from translator import translate_to_tamil, save_history, load_history, get_history_files
    from utils import get_selected_text, is_valid_selection
    from gui import show_translation_popup
except ImportError as exc:
    messagebox.showerror("Import Error", str(exc))
    sys.exit(1)


class App:
    """Main application window."""

    START_W, START_H = 400, 460

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.last_selection = ""
        self.running = False
        self.auto_thread: threading.Thread | None = None
        self.selection_timer = None
        self.pending_selection = ""
        self.recent_translations = {}  # Cache to prevent duplicate translations
        self.translation_cooldown = 5  # Seconds before same word can be translated again
        self.dialog_active = False  # Track if any dialog is open

        self._window()
        self._styles()
        self._widgets()

        # Remove the Alt+H hotkey since we're removing the history button
        self.start()  # begin auto‑translate immediately

    # ───────────────────────────── window & style ───────────────────────────
    def _window(self) -> None:
        self.root.title("Tamil‑English Translator")
        self.root.geometry(f"{self.START_W}x{self.START_H}")
        self.root.minsize(self.START_W, self.START_H)
        self.root.resizable(True, True)
        self.root.attributes("-topmost", True)

        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{self.START_W}x{self.START_H}+{sw//2-self.START_W//2}+{sh//2-self.START_H//2}")

    def _styles(self) -> None:
        s = ttk.Style()
        s.configure("H.TButton", background="#4A4A4A", foreground="black", font=("Arial", 9, "bold"), borderwidth=0)
        s.map("H.TButton", background=[("active", "#5A5A5A")])
        s.configure("Q.TButton", background="#8B0000", foreground="black", font=("Arial", 9, "bold"), borderwidth=0)
        s.map("Q.TButton", background=[("active", "#A50000")])
        s.configure("T.TButton", background="#4CAF50", foreground="black", font=("Arial", 8, "bold"), borderwidth=0)
        s.map("T.TButton", background=[("active", "#45a049")])

    # ───────────────────────────── widgets ────────────────────────────────
    def _widgets(self) -> None:
        main = tk.Frame(self.root, bg="#E8E8E8", padx=12, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(main, bg="#8B7FB8")
        card.pack(fill=tk.BOTH, expand=True)

        # Header bar
        hdr = tk.Frame(card, bg="#2C2C2C", height=50)
        hdr.pack(fill=tk.X, padx=10, pady=(10, 0))
        hdr.pack_propagate(False)

        icon = tk.Canvas(hdr, width=28, height=28, bg="#2C2C2C", highlightthickness=0)
        icon.pack(side=tk.LEFT, padx=(14, 6), pady=8)
        icon.create_oval(2, 2, 26, 26, fill="#FF6B35", outline="")
        icon.create_text(14, 14, text="T", fill="white", font=("Arial", 12, "bold"))

        tk.Label(hdr, text="Tamil‑English Translator", fg="white", bg="#2C2C2C", font=("Arial", 12, "bold")).pack(side=tk.LEFT, pady=12)
        self.status_lbl = tk.Label(hdr, text="🟢", fg="#90EE90", bg="#2C2C2C", font=("Arial", 8))
        self.status_lbl.pack(side=tk.RIGHT, padx=(0, 12), pady=12)

        # Body area
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

        # Footer bar - Removed History button
        foot = tk.Frame(card, bg="#8B7FB8")
        foot.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.toggle_btn = ttk.Button(foot, text="Disable Auto", style="T.TButton", command=self._toggle_auto)
        self.toggle_btn.pack(side=tk.LEFT, padx=(6, 3), ipadx=8, ipady=4)
        ttk.Button(foot, text="Edit History", style="H.TButton", command=self.show_edit_history).pack(side=tk.LEFT, padx=3, ipadx=8, ipady=4)
        ttk.Button(foot, text="Quit", style="Q.TButton", command=self._quit).pack(side=tk.RIGHT, padx=(0, 6), ipadx=10, ipady=4)

    # ───────────────────────────── runtime control ───────────────────────────
    def start(self) -> None:
        """Start the background auto‑translate thread."""
        if self.running:
            return
        self.running = True
        self.auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
        self.auto_thread.start()
        self._refresh_history()

    def _already_translated_recently(self, text: str) -> bool:
        """Check if text was already translated recently by looking at history."""
        try:
            # Load recent history (last 50 entries to avoid performance issues)
            history = load_history()
            recent_entries = history[-50:] if len(history) > 50 else history
            
            # Check if this exact text exists in recent history
            text_lower = text.lower().strip()
            for entry in recent_entries:
                if len(entry) >= 2:
                    original = entry[0].lower().strip()
                    if original == text_lower:
                        return True
            return False
        except Exception:
            return False

    def _is_app_window_focused(self) -> bool:
        """Check if the translator app window is currently focused."""
        try:
            return self.root.focus_get() is not None
        except:
            return False

    def _is_dialog_text(self, text: str) -> bool:
        """Check if the text is from a dialog box that should not be translated."""
        dialog_indicators = [
            "success", "deleted", "translation", "error", "warning", "info",
            "confirm", "ok", "cancel", "yes", "no", "close", "save", "open",
            "வெற்றி", "நீக்கியது", "மொழிபெயர்ப்பு", "பிழை", "எச்சரிக்கை",
            "------------------------", "---", ":::", ">>>", "<<<",
            "Invalid Input", "Both fields are required", "No Selection",
            "Please select", "Are you sure", "This action cannot be undone"
        ]
        
        text_lower = text.lower().strip()
        
        # Check for dialog indicators
        for indicator in dialog_indicators:
            if indicator.lower() in text_lower:
                return True
        
        # Check for patterns that suggest dialog text
        if any(pattern in text_lower for pattern in ["--", "***", ">>>"]):
            return True
            
        # Check for very short text that's likely UI elements
        if len(text_lower) < 2:
            return True
            
        return False

    def _should_translate_selection(self, sel: str) -> bool:
        """Enhanced validation for whether a selection should be translated."""
        if not sel or not sel.strip():
            return False
        
        # Skip if app window is focused (prevents UI elements from being translated)
        if self._is_app_window_focused():
            return False
        
        # Skip if any dialog is currently active
        if self.dialog_active:
            return False
        
        # Skip dialog text
        if self._is_dialog_text(sel):
            return False
        
        # Skip very short selections (likely UI elements)
        if len(sel.strip()) < 3:
            return False
        
        # Clean the selection for comparison
        clean_sel = sel.strip().lower()
        
        # Check if we recently translated this exact text (in-memory cache)
        current_time = time.time()
        if clean_sel in self.recent_translations:
            last_translation_time = self.recent_translations[clean_sel]
            if current_time - last_translation_time < self.translation_cooldown:
                return False
        
        # Check if this text already exists in history files
        if self._already_translated_recently(sel.strip()):
            return False
        
        # Skip if selection is the same as last one
        if sel == self.last_selection:
            return False
        
        # Skip common UI elements and single words that are likely UI
        ui_elements = {
            'quit', 'yes', 'no', 'ok', 'cancel', 'close', 'minimize', 'maximize',
            'file', 'edit', 'view', 'help', 'tools', 'options', 'settings',
            'save', 'open', 'new', 'copy', 'paste', 'cut', 'undo', 'redo',
            'authenticated', 'login', 'password', 'username', 'submit', 'error',
            'success', 'loading', 'refresh', 'reload', 'back', 'forward', 'home'
        }
        
        if clean_sel in ui_elements:
            return False
        
        # Use existing validation
        return is_valid_selection(sel)

    def _delayed_translate(self, sel: str) -> None:
        """Translate selection after a delay to ensure complete selection."""
        if self.selection_timer:
            self.selection_timer.cancel()
        
        self.pending_selection = sel
        self.selection_timer = threading.Timer(0.8, self._execute_translation)
        self.selection_timer.start()

    def _execute_translation(self) -> None:
        """Execute the translation if conditions are still met."""
        if not self.running or not self.pending_selection:
            return
        
        # Re-check conditions
        if not self._should_translate_selection(self.pending_selection):
            return
        
        # Check if selection has changed (user might still be selecting)
        try:
            current_sel = get_selected_text()
            if current_sel and current_sel != self.pending_selection:
                return  # Selection changed, don't translate
        except:
            pass
        
        ta = translate_to_tamil(self.pending_selection)
        if ta:
            # Mark this translation as recent
            clean_sel = self.pending_selection.strip().lower()
            self.recent_translations[clean_sel] = time.time()
            
            # Clean old entries to prevent memory buildup
            current_time = time.time()
            self.recent_translations = {
                k: v for k, v in self.recent_translations.items()
                if current_time - v < self.translation_cooldown * 2
            }
            
            self.last_selection = self.pending_selection
            save_history(self.pending_selection, ta)
            self.root.after(0, self._refresh_history)
            threading.Thread(target=show_translation_popup, args=(ta,), daemon=True).start()

    def _auto_loop(self) -> None:
        while self.running:
            time.sleep(0.5)  # Reduced sleep time for better responsiveness
            try:
                sel = get_selected_text()
            except Exception:
                sel = ""
            
            if sel and self._should_translate_selection(sel):
                self._delayed_translate(sel)

    # ───────────────────────────── callbacks ────────────────────────────────
    def _toggle_auto(self) -> None:
        if self.running:
            # turn OFF
            self.running = False
            if self.selection_timer:
                self.selection_timer.cancel()
            self.toggle_btn.config(text="Enable Auto")
            self.status_lbl.config(text="🔴", fg="#FFB6C1")
        else:
            # turn ON
            self.toggle_btn.config(text="Disable Auto")
            self.status_lbl.config(text="🟢", fg="#90EE90")
            self.start()

    def _manual_translate(self) -> None:
        en = self.input_txt.get("1.0", tk.END).strip()
        if not en or not any(c.isalpha() for c in en):
            self.dialog_active = True
            messagebox.showwarning("Warning", "Enter valid English text.")
            self.dialog_active = False
            return
        ta = translate_to_tamil(en)
        if ta:
            save_history(en, ta)
            self._refresh_history()
            # Show translation popup for manual translation too
            threading.Thread(target=show_translation_popup, args=(ta,), daemon=True).start()

    def _refresh_history(self) -> None:
        """Refresh the history display in the main window."""
        records = load_history()
        self.history_txt.config(state=tk.NORMAL)
        self.history_txt.delete("1.0", tk.END)
        for en, ta in reversed(records[-10:]):
            self.history_txt.insert(tk.END, f"{en} - {ta}\n{'-' * 40}\n")
        self.history_txt.config(state=tk.DISABLED)

    def show_edit_history(self) -> None:
        """Show the editable history window."""
        self.dialog_active = True
        self._create_history_editor()

    def _create_history_editor(self) -> None:
        """Create a window for editing translation history."""
        editor_window = tk.Toplevel(self.root)
        editor_window.title("Edit Translation History")
        editor_window.geometry("800x600")
        editor_window.resizable(True, True)
        
        # Make it stay on top
        editor_window.attributes("-topmost", True)
        
        # Set dialog_active to False when window is closed
        def on_close():
            self.dialog_active = False
            editor_window.destroy()
        
        editor_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Main frame
        main_frame = tk.Frame(editor_window, bg="#E8E8E8", padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Translation History Editor", 
                              font=("Arial", 14, "bold"), bg="#E8E8E8")
        title_label.pack(pady=(0, 10))
        
        # Search frame
        search_frame = tk.Frame(main_frame, bg="#E8E8E8")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", bg="#E8E8E8", font=("Arial", 9)).pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 9))
        search_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        
        # Buttons frame
        button_frame = tk.Frame(main_frame, bg="#E8E8E8")
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create Treeview with scrollbars
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("Original", "Translation")
        tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings", height=15)
        tree.heading("#0", text="ID")
        tree.heading("Original", text="Original Text")
        tree.heading("Translation", text="Tamil Translation")
        
        # Configure column widths
        tree.column("#0", width=50, minwidth=50)
        tree.column("Original", width=300, minwidth=200)
        tree.column("Translation", width=300, minwidth=200)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Load history data
        history_data = load_history()
        
        def populate_tree(filter_text=""):
            """Populate the tree with history data."""
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
            
            # Add filtered items
            for idx, (original, translation) in enumerate(history_data):
                if not filter_text or filter_text.lower() in original.lower() or filter_text.lower() in translation.lower():
                    tree.insert("", tk.END, iid=idx, text=str(idx + 1), 
                              values=(original, translation))
        
        def on_search(*args):
            """Filter the tree based on search text."""
            populate_tree(search_var.get())
        
        def edit_selected():
            """Edit the selected translation."""
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select a translation to edit.")
                return
            
            item_id = selected[0]
            values = tree.item(item_id, "values")
            if not values:
                return
            
            original_text, translation_text = values
            
            # Create edit dialog
            edit_dialog = tk.Toplevel(editor_window)
            edit_dialog.title("Edit Translation")
            edit_dialog.geometry("500x300")
            edit_dialog.resizable(True, True)
            edit_dialog.attributes("-topmost", True)
            
            # Center the dialog
            edit_dialog.update_idletasks()
            x = editor_window.winfo_x() + (editor_window.winfo_width() // 2) - (edit_dialog.winfo_width() // 2)
            y = editor_window.winfo_y() + (editor_window.winfo_height() // 2) - (edit_dialog.winfo_height() // 2)
            edit_dialog.geometry(f"+{x}+{y}")
            
            frame = tk.Frame(edit_dialog, padx=20, pady=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Original text
            tk.Label(frame, text="Original Text:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
            original_var = tk.StringVar(value=original_text)
            original_entry = tk.Entry(frame, textvariable=original_var, font=("Arial", 10))
            original_entry.pack(fill=tk.X, pady=(5, 15))
            
            # Translation text
            tk.Label(frame, text="Tamil Translation:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
            translation_var = tk.StringVar(value=translation_text)
            translation_entry = tk.Entry(frame, textvariable=translation_var, font=("Arial", 10))
            translation_entry.pack(fill=tk.X, pady=(5, 20))
            
            # Buttons
            btn_frame = tk.Frame(frame)
            btn_frame.pack(fill=tk.X)
            
            def save_edit():
                new_original = original_var.get().strip()
                new_translation = translation_var.get().strip()
                
                if not new_original or not new_translation:
                    messagebox.showwarning("Invalid Input", "Both fields are required.")
                    return
                
                # Update the data
                idx = int(item_id)
                history_data[idx] = (new_original, new_translation)
                
                # Update tree
                tree.item(item_id, values=(new_original, new_translation))
                
                # Save changes to file immediately
                try:
                    # Clear existing history files
                    for file_path in get_history_files():
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # Save updated history
                    if history_data:
                        from translator import get_latest_history_file
                        current_file = get_latest_history_file()
                        with open(current_file, "w", newline='', encoding='utf-8') as file:
                            writer = csv.writer(file)
                            for original, translation in history_data:
                                writer.writerow([original, translation])
                    
                    # Refresh the main window history display
                    self._refresh_history()
                    
                    edit_dialog.destroy()
                    messagebox.showinfo("Success", "Translation updated successfully!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
            
            tk.Button(btn_frame, text="Save", command=save_edit, 
                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
            tk.Button(btn_frame, text="Cancel", command=edit_dialog.destroy,
                     bg="#f44336", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        def delete_selected():
            """Delete the selected translation(s)."""
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select translation(s) to delete.")
                return
            
            if messagebox.askyesno("Confirm Delete", 
                                 f"Are you sure you want to delete {len(selected)} translation(s)?"):
                # Sort indices in reverse order to avoid index shifting issues
                indices_to_delete = sorted([int(item_id) for item_id in selected], reverse=True)
                
                for idx in indices_to_delete:
                    del history_data[idx]
                
                # Save changes to file immediately
                try:
                    # Clear existing history files
                    for file_path in get_history_files():
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # Save updated history
                    if history_data:
                        from translator import get_latest_history_file
                        current_file = get_latest_history_file()
                        with open(current_file, "w", newline='', encoding='utf-8') as file:
                            writer = csv.writer(file)
                            for original, translation in history_data:
                                writer.writerow([original, translation])
                    
                    # Refresh the main window history display
                    self._refresh_history()
                    
                    # Refresh the tree
                    populate_tree(search_var.get())
                    messagebox.showinfo("Success", f"Deleted {len(selected)} translation(s)!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save changes: {str(e)}")
        
        def clear_all_history():
            """Clear all translation history."""
            if messagebox.askyesno("Confirm Clear All", 
                                 "Are you sure you want to delete ALL translation history?\n\nThis action cannot be undone!"):
                history_data.clear()
                
                # Save changes to file immediately
                try:
                    # Clear existing history files
                    for file_path in get_history_files():
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # Refresh the main window history display
                    self._refresh_history()
                    
                    populate_tree()
                    messagebox.showinfo("Success", "All history cleared!")
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to clear history: {str(e)}")
        
        # Bind search
        search_var.trace("w", on_search)
        
        # Buttons
        tk.Button(button_frame, text="Edit Selected", command=edit_selected,
                 bg="#2196F3", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(button_frame, text="Delete Selected", command=delete_selected,
                 bg="#f44336", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear All", command=clear_all_history,
                 bg="#FF5722", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Close", command=on_close,
                 bg="#9E9E9E", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT)
        
        # Initial population
        populate_tree()
        
        # Focus on search entry
        search_entry.focus_set()

    def _quit(self) -> None:
        if messagebox.askyesno("Quit", "Are you sure?"):
            self.running = False
            if self.selection_timer:
                self.selection_timer.cancel()
            self.root.quit()

def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app._quit)
    root.mainloop()


if __name__ == "__main__":
    main()