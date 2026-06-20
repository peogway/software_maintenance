from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class IssueBooksFrame(BaseModuleFrame):
    """Issue and return book workflow."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_issue_id = None
        self.member_options = {}
        self.book_options = {}
        self.member_var = tk.StringVar()
        self.book_var = tk.StringVar()
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Issue / Return Books",
            "Assign books to members, calculate due dates, and collect return fines automatically.",
        )

        top = tk.Frame(self, bg=COLORS["bg"])
        top.pack(fill="x", padx=24, pady=(0, 16))

        issue_panel = self.create_panel(top)

        issue_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))
        issue_panel.configure(padx=18, pady=18)

        tk.Label(
            issue_panel,
            text="Issue Book",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        tk.Label(
            issue_panel,
            text="Member",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=1, column=0, sticky="w", padx=6)
        self.member_combo = ttk.Combobox(
            issue_panel, textvariable=self.member_var, state="readonly", width=42
        )
        self.member_combo.grid(
            row=2, column=0, sticky="ew", padx=6, pady=(0, 10), columnspan=2
        )

        tk.Label(
            issue_panel,
            text="Book",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=3, column=0, sticky="w", padx=6)
        self.book_combo = ttk.Combobox(
            issue_panel, textvariable=self.book_var, state="readonly", width=42
        )
        self.book_combo.grid(
            row=4, column=0, sticky="ew", padx=6, pady=(0, 10), columnspan=2
        )

        self.create_button(
            issue_panel, "Issue Book", self.issue_book, COLORS["primary"]
        ).grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))

        return_panel = self.create_panel(top)
        return_panel.pack(side="right", fill="both", expand=True)
        return_panel.configure(padx=18, pady=18)

        tk.Label(
            return_panel,
            text="Return Book",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.issue_id_label = tk.Label(
            return_panel,
            text="Select an issued record from the table below.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["body"],
            wraplength=360,
            justify="left",
        )
        self.issue_id_label.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 14))

        self.create_button(
            return_panel,
            "Return Selected",
            self.return_selected_book,
            COLORS["success"],
        ).grid(row=2, column=0, sticky="ew", padx=6)

        bottom = self.create_panel(self)
        bottom.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        table_wrap = self.create_panel(bottom)
        table_wrap.configure(padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = [
            "id",
            "book_code",
            "title",
            "member_code",
            "member_name",
            "issue_date",
            "due_date",
            "return_date",
            "status",
            "fine_amount",
        ]

        widths = {
            "id": 60,
            "book_code": 90,
            "title": 180,
            "member_code": 100,
            "member_name": 160,
            "issue_date": 110,
            "due_date": 110,
            "return_date": 110,
            "status": 90,
            "fine_amount": 90,
        }

        self.tree, scrollbar = self.build_treeview(table_wrap, columns, widths)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        issue_panel.columnconfigure((0, 1), weight=1)
        return_panel.columnconfigure(0, weight=1)

    def _load_member_options(self) -> None:
        members = self.db.fetch_members(order_by="name")
        self.member_options = {
            f"{member['member_code']} - {member['name']}": member["id"]
            for member in members
        }
        self.member_combo["values"] = list(self.member_options.keys())
        if self.member_options:
            if self.member_var.get() not in self.member_options:
                self.member_var.set(next(iter(self.member_options.keys())))
        else:
            self.member_var.set("")

    def _load_book_options(self) -> None:
        books = self.db.report_available_books()
        self.book_options = {
            f"{book['book_code']} - {book['title']} (Avail: {book['available_quantity']})": book[
                "id"
            ]
            for book in books
        }
        self.book_combo["values"] = list(self.book_options.keys())
        if self.book_options:
            if self.book_var.get() not in self.book_options:
                self.book_var.set(next(iter(self.book_options.keys())))
        else:
            self.book_var.set("")

    def _selected_member_id(self) -> int | None:
        return self.member_options.get(self.member_var.get())

    def _selected_book_id(self) -> int | None:
        return self.book_options.get(self.book_var.get())

    def issue_book(self) -> None:
        member_id = self._selected_member_id()
        book_id = self._selected_book_id()
        if member_id is None or book_id is None:
            messagebox.showwarning(
                "Selection Required", "Select both a member and a book."
            )
            return
        try:
            self.db.issue_book(book_id, member_id)
            messagebox.showinfo("Success", "Book issued successfully.")
            self.refresh_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def return_selected_book(self) -> None:
        if self.selected_issue_id is None:
            messagebox.showwarning(
                "Selection Required", "Select an issued record to return."
            )
            return
        try:
            fine = self.db.return_book(self.selected_issue_id)
            messagebox.showinfo(
                "Success", f"Book returned successfully. Fine: Tk {fine:.2f}"
            )
            self.refresh_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def load_data(self) -> None:
        issues = self.db.fetch_issued_books()
        self.fill_treeview(
            self.tree,
            [
                (
                    issue["id"],
                    issue["book_code"],
                    issue["title"],
                    issue["member_code"],
                    issue["member_name"],
                    issue["issue_date"],
                    issue["due_date"],
                    issue["return_date"] or "",
                    issue["status"],
                    f"Tk {issue['fine_amount']:.2f}",
                )
                for issue in issues
            ],
        )

    def refresh_data(self) -> None:
        self.selected_issue_id = None
        self._load_member_options()
        self._load_book_options()
        self.load_data()
        self.issue_id_label.configure(
            text="Select an issued record from the table below."
        )

    def on_select(self, event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.selected_issue_id = int(values[0])
        status_text = f"Selected Issue ID: {values[0]} | Status: {values[8]}"
        self.issue_id_label.configure(text=status_text)
