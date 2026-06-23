from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable, Optional, Sequence, Callable, Any
from tkinter import messagebox

COLORS = {
    "bg": "#0f172a",
    "panel": "#111c33",
    "panel_alt": "#172554",
    "card": "#1e293b",
    "primary": "#2563eb",
    "primary_dark": "#1d4ed8",
    "secondary": "#334155",
    "accent": "#38bdf8",
    "success": "#16a34a",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text": "#f8fafc",
    "muted": "#cbd5e1",
    "entry_bg": "#f8fafc",
    "table_bg": "#ffffff",
}

FONTS = {
    "title": ("Segoe UI", 18, "bold"),
    "subtitle": ("Segoe UI", 10),
    "heading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 10),
    "button": ("Segoe UI", 10, "bold"),
    "card_value": ("Segoe UI", 22, "bold"),
    "card_label": ("Segoe UI", 10, "bold"),
}


class BaseModuleFrame(tk.Frame):
    """Common scaffolding for application module screens."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.db = db
        self.selected_id = None
        self.sort_column = None
        self.sort_ascending = True
        self.search_field_var = None
        self.search_text_var = None
        self.form_fields = {}

    def build_button(
        self, parent, text: str, command: Callable[[], None], color: str
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            relief="flat",
            font=FONTS["button"],
        )

    def build_panel(self, parent):
        return tk.Frame(
            parent,
            bg=COLORS["panel"],
            bd=0,
            highlightthickness=1,
            highlightbackground="#22314f",
        )

    def build_heading(self, title: str, subtitle: str = "") -> tk.Frame:
        container = tk.Frame(self, bg=COLORS["bg"])
        container.pack(fill="x", padx=24, pady=(18, 12))

        title_label = tk.Label(
            container,
            text=title,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=FONTS["title"],
        )
        title_label.pack(anchor="w")

        if subtitle:
            subtitle_label = tk.Label(
                container,
                text=subtitle,
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=FONTS["subtitle"],
            )
            subtitle_label.pack(anchor="w", pady=(4, 0))

        return container

    def build_card(
        self, parent: tk.Widget, title: str, value: str, accent: str
    ) -> tk.Frame:
        card = self.build_panel(parent)
        card.configure(bg=COLORS["card"])
        card.pack_propagate(False)

        accent_bar = tk.Frame(card, bg=accent, height=4)
        accent_bar.pack(fill="x", side="top")

        title_label = tk.Label(
            card,
            text=title,
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=FONTS["card_label"],
        )
        title_label.pack(anchor="w", padx=16, pady=(16, 6))

        value_label = tk.Label(
            card,
            text=value,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=FONTS["card_value"],
        )
        value_label.pack(anchor="w", padx=16, pady=(0, 16))
        return card

    def labeled_entry(
        self,
        parent: tk.Widget,
        label_text: str,
        row: int,
        column: int,
        width: int = 28,
        show: str | None = None,
        readonly: bool = False,
    ) -> tk.Entry:
        label = tk.Label(
            parent,
            text=label_text,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        )
        label.grid(row=row, column=column, sticky="w", padx=8, pady=(8, 3))

        entry = tk.Entry(
            parent,
            width=width,
            show=show,
            relief="flat",
            bg=COLORS["entry_bg"],
            fg="#0f172a",
            insertbackground="#0f172a",
            font=FONTS["body"],
        )
        entry.grid(row=row + 1, column=column, sticky="ew", padx=8, pady=(0, 8))
        if readonly:
            entry.configure(state="readonly")
        return entry

    def labeled_text(
        self, parent: tk.Widget, label_text: str, row: int, column: int, height: int = 4
    ) -> tk.Text:
        label = tk.Label(
            parent,
            text=label_text,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        )
        label.grid(row=row, column=column, sticky="w", padx=8, pady=(8, 3))

        text = tk.Text(
            parent,
            height=height,
            relief="flat",
            bg=COLORS["entry_bg"],
            fg="#0f172a",
            insertbackground="#0f172a",
            font=FONTS["body"],
            wrap="word",
        )
        text.grid(row=row + 1, column=column, sticky="ew", padx=8, pady=(0, 8))
        return text

    def configure_treeview(
        self,
        tree: ttk.Treeview,
        columns: Sequence[str],
        widths: dict[str, int] | None = None,
    ) -> None:
        tree["columns"] = columns
        tree["show"] = "headings"
        for column in columns:
            tree.heading(column, text=column.replace("_", " ").title())
            tree.column(
                column, width=widths.get(column, 130), anchor="center", stretch=True
            )

        for column in columns:
            tree.heading(
                column,
                text=column.replace("_", " ").title(),
                command=lambda c=column: self.set_sort(c),
            )

    def build_table(self, parent, columns, widths=None):
        widths = widths or {}

        tree = ttk.Treeview(parent, columns=columns, show="headings")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        self.configure_treeview(tree, columns, widths or {})

        if self.on_select:
            tree.bind("<<TreeviewSelect>>", self.on_select)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return tree, scrollbar

    def fill_treeview(
        self, tree: ttk.Treeview, rows: Iterable[Sequence[object]]
    ) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", "end", values=row)

    def clear_entries(self, *widgets) -> None:
        for widget in widgets:
            if isinstance(widget, tk.Entry):
                state = str(widget.cget("state"))
                if state == "readonly":
                    widget.configure(state="normal")
                    widget.delete(0, tk.END)
                    widget.configure(state="readonly")
                else:
                    widget.delete(0, tk.END)
            elif isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            elif isinstance(widget, tk.StringVar):
                value = widget.get().strip()
                if value == "admin" or value == "staff" or value == "student":
                    widget.set("staff")
                else:
                    widget.set("")

    def load_data(self):
        pass

    def on_select(
        self,
        fn: Optional[Callable[[], None]] = None,
        parse_int: bool = False,
        isse_selection: bool = False,
        code_entry: bool = False,
        report: bool = False,
    ) -> None:
        self.clear_entries(self.form_fields.values())
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        value = values[0]

        if parse_int or isse_selection:
            value = int(value)

        if code_entry:
            self.code_entry.configure(state="normal")

        if isse_selection:
            self.selected_id = value
            status_text = f"Selected Issue ID: {values[0]} | Status: {values[8]}"
            self.issue_id_label.configure(text=status_text)
        else:
            selected = fn(value)
            if not selected:
                return
            self.selected_id = selected["id"]
            self.fill_form_data(self.form_fields, selected)

    def set_sort(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self.load_data()

    def _reset_search(self, field: str) -> None:
        self.search_field_var.set(field)
        self.search_text_var.set("")
        self.load_data()

    def safe_fn(
        self,
        fn: Callable[[], Any],
        error_type: str = "Error",
        fail_msg: Optional[str] = "",
        success_type: str = "Successs",
        success_msg: Optional[str] = "",
        display_success_message=True,
        load_data: bool = False,
        clear_form: bool = False,
        refresh_data=False,
    ) -> bool | Any:
        try:
            res = fn()
            if clear_form:
                self.clear_form()
            if load_data:
                self.load_data()
            if refresh_data:
                self.refresh_data()

            if not display_success_message:
                return res

            if success_msg:
                messagebox.showinfo(success_type, success_msg)
            return True
        except Exception as e:
            messagebox.showwarning(error_type, fail_msg or str(e))
            return False

    def clear_form(self, user_page: bool = False) -> None:
        self.selected_id = None
        self.clear_entries(*self.form_fields.values())

        if not user_page:
            self._set_code()
        self.tree.selection_remove(self.tree.selection())

    def refresh_data(self) -> None:
        self._set_code()
        self.load_data()

    def get_form_data(self, fields):
        data = {}
        for key, widget in fields.items():
            if isinstance(widget, tk.Text):
                data[key] = widget.get("1.0", tk.END).strip()
            else:
                data[key] = widget.get().strip()

        return data

    def fill_form_data(self, fields, data):
        for key, widget in fields.items():
            value = data.get(key, "")

            self.clear_entries(widget)

            if isinstance(widget, tk.Text):
                widget.insert("1.0", value)
            elif isinstance(widget, tk.StringVar):
                widget.set(value)
            else:
                widget.insert(0, value)

    def _collect_data(self):
        return self.get_form_data(self.form_fields)

    def _set_code(self) -> None:
        code = self._get_code()
        self.code_entry.configure(state="normal")
        self.code_entry.delete(0, tk.END)
        self.code_entry.insert(0, code)
        self.code_entry.configure(state="readonly")

    def _get_code(self) -> str:
        pass
