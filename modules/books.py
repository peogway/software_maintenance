from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class BooksFrame(BaseModuleFrame):
    """Book management screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_id = None
        self.search_field_var = tk.StringVar(value="title")
        self.search_text_var = tk.StringVar()
        self.sort_column = "title"
        self.sort_ascending = True
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Book Management",
            "Add, edit, delete, and search books. Book codes are generated automatically.",
        )

        search_bar = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=14)
        search_bar.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(
            search_bar,
            text="Search By",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=0, column=0, sticky="w", padx=6)
        self.search_field = ttk.Combobox(
            search_bar,
            textvariable=self.search_field_var,
            values=["title", "author", "isbn", "category"],
            state="readonly",
            width=16,
        )
        self.search_field.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(
            search_bar,
            text="Keyword",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=0, column=2, sticky="w", padx=6)
        self.search_entry = tk.Entry(
            search_bar, textvariable=self.search_text_var, width=28, relief="flat"
        )
        self.search_entry.grid(row=0, column=3, padx=6, pady=6)

        self.build_button(search_bar, "Search", self.load_data, COLORS["primary"]).grid(
            row=0, column=4, padx=6
        )

        self.build_button(
            search_bar,
            "Reset",
            lambda: self._reset_search("title"),
            COLORS["secondary"],
        ).grid(row=0, column=5, padx=6)

        search_bar.columnconfigure(6, weight=1)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        left = self.build_panel(content)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=440)
        left.pack_propagate(False)

        form = tk.Frame(left, bg=COLORS["panel"], padx=10, pady=10)
        form.pack(fill="both", expand=True)

        self.code_entry = self.labeled_entry(form, "Book Code", 0, 0, readonly=True)
        self.title_entry = self.labeled_entry(form, "Title", 0, 1)
        self.author_entry = self.labeled_entry(form, "Author", 2, 0)
        self.category_entry = self.labeled_entry(form, "Category", 2, 1)
        self.publisher_entry = self.labeled_entry(form, "Publisher", 4, 0)
        self.isbn_entry = self.labeled_entry(form, "ISBN", 4, 1)
        self.quantity_entry = self.labeled_entry(form, "Quantity", 6, 0)
        self.shelf_entry = self.labeled_entry(form, "Shelf Location", 6, 1)

        action_row = tk.Frame(form, bg=COLORS["panel"])
        action_row.grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 0)
        )
        action_row.columnconfigure((0, 1, 2, 3), weight=1)

        self.build_button(action_row, "Add", self.add_book, COLORS["success"]).grid(
            row=0, column=0, sticky="ew", padx=3
        )

        self.build_button(
            action_row, "Update", self.update_book, COLORS["warning"]
        ).grid(row=0, column=1, sticky="ew", padx=3)

        self.build_button(
            action_row, "Delete", self.delete_book, COLORS["danger"]
        ).grid(row=0, column=2, sticky="ew", padx=3)

        self.build_button(
            action_row, "Clear", self.clear_form, COLORS["secondary"]
        ).grid(row=0, column=3, sticky="ew", padx=3)

        right = self.build_panel(content)
        right.pack(side="right", fill="both", expand=True)

        table_wrap = tk.Frame(right, bg=COLORS["panel"], padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = [
            "book_code",
            "title",
            "author",
            "category",
            "publisher",
            "isbn",
            "quantity",
            "available_quantity",
            "reserved_quantity",
            "shelf_location",
            "added_date",
        ]

        widths = {
            "book_code": 90,
            "title": 170,
            "author": 140,
            "category": 120,
            "publisher": 140,
            "isbn": 130,
            "quantity": 80,
            "available_quantity": 110,
            "reserved_quantity": 110,
            "shelf_location": 110,
            "added_date": 120,
        }

        self.tree, self.scrollbar = self.build_table(table_wrap, columns, widths)

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self.form_fields = {
            "book_code": self.code_entry,
            "title": self.title_entry,
            "author": self.author_entry,
            "category": self.category_entry,
            "publisher": self.publisher_entry,
            "isbn": self.isbn_entry,
            "quantity": self.quantity_entry,
            "shelf_location": self.shelf_entry,
        }

    def _get_code(self) -> None:
        return self.db.generate_book_code()

    def _validate(self, data: dict) -> bool:
        required = [
            "title",
            "author",
            "category",
            "publisher",
            "isbn",
            "quantity",
            "shelf_location",
        ]
        for field in required:
            if not data[field]:
                messagebox.showwarning(
                    "Validation Error",
                    f"{field.replace('_', ' ').title()} is required.",
                )
                return False

        success = self.safe_fn(
            lambda: int(data["quantity"]),
            error_type="Validation Error",
            fail_msg="Quantity must be a positive whole number.",
        )

        if not success:
            return False

        return True

    def add_book(self) -> None:
        data = self._collect_data()
        if not self._validate(data):
            return

        success = self.safe_fn(
            lambda: self.db.add_book(data),
            success_msg="Book added successfully.",
            load_data=True,
            clear_form=True,
        )

    def update_book(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Selection Required", "Select a book to update.")
            return
        data = self._collect_data()
        if not self._validate(data):
            return

        success = self.safe_fn(
            lambda: self.db.update_book(self.selected_id, data),
            success_msg="Book updated successfully.",
            load_data=True,
        )

    def delete_book(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Selection Required", "Select a book to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected book?"):
            return

        success = self.safe_fn(
            lambda: self.db.delete_book(self.selected_id),
            success_msg="Book deleted successfully.",
            clear_form=True,
            load_data=True,
        )

    def load_data(self) -> None:
        search_text = self.search_text_var.get().strip()
        field = self.search_field_var.get().strip() or "title"
        books = self.db.fetch_books(
            search_text, field, self.sort_column, self.sort_ascending
        )
        self.fill_treeview(
            self.tree,
            [
                (
                    book["book_code"],
                    book["title"],
                    book["author"],
                    book["category"],
                    book["publisher"],
                    book["isbn"],
                    book["quantity"],
                    book["available_quantity"],
                    book["reserved_quantity"],
                    book["shelf_location"],
                    book["added_date"],
                )
                for book in books
            ],
        )

    def on_select(self, event) -> None:
        super().on_select(self.db.get_book_by_code, code_entry=True)
