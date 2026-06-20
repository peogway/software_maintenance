from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class BooksFrame(BaseModuleFrame):
    """Book management screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_book_id = None
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

        self.create_button(
            search_bar, "Search", self.load_data, COLORS["primary"]
        ).grid(row=0, column=4, padx=6)

        self.create_button(
            search_bar, "Reset", self._reset_search, COLORS["secondary"]
        ).grid(row=0, column=5, padx=6)

        search_bar.columnconfigure(6, weight=1)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        left = self.create_panel(content)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=440)
        left.pack_propagate(False)

        form = tk.Frame(left, bg=COLORS["panel"], padx=10, pady=10)
        form.pack(fill="both", expand=True)

        self.book_code_entry = self.labeled_entry(
            form, "Book Code", 0, 0, readonly=True
        )
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

        self.create_button(action_row, "Add", self.add_book, COLORS["success"]).grid(
            row=0, column=0, sticky="ew", padx=3
        )

        self.create_button(
            action_row, "Update", self.update_book, COLORS["warning"]
        ).grid(row=0, column=1, sticky="ew", padx=3)

        self.create_button(
            action_row, "Delete", self.delete_book, COLORS["danger"]
        ).grid(row=0, column=2, sticky="ew", padx=3)

        self.create_button(
            action_row, "Clear", self.clear_form, COLORS["secondary"]
        ).grid(row=0, column=3, sticky="ew", padx=3)

        right = self.create_panel(content)
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
            "shelf_location",
            "added_date",
        ]
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", selectmode="browse"
        )
        widths = {
            "book_code": 90,
            "title": 170,
            "author": 140,
            "category": 120,
            "publisher": 140,
            "isbn": 130,
            "quantity": 80,
            "available_quantity": 110,
            "shelf_location": 110,
            "added_date": 120,
        }
        self.configure_treeview(self.tree, columns, widths)
        for column in columns:
            self.tree.heading(
                column,
                text=column.replace("_", " ").title(),
                command=lambda c=column: self.sort_by(c),
            )
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            table_wrap, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

    def _reset_search(self) -> None:
        self.search_field_var.set("title")
        self.search_text_var.set("")
        self.load_data()

    def _set_book_code(self) -> None:
        code = self.db.generate_book_code()
        self.book_code_entry.configure(state="normal")
        self.book_code_entry.delete(0, tk.END)
        self.book_code_entry.insert(0, code)
        self.book_code_entry.configure(state="readonly")

    def clear_form(self) -> None:
        self.selected_book_id = None
        self.clear_entries(
            self.book_code_entry,
            self.title_entry,
            self.author_entry,
            self.category_entry,
            self.publisher_entry,
            self.isbn_entry,
            self.quantity_entry,
            self.shelf_entry,
        )
        self._set_book_code()
        self.tree.selection_remove(self.tree.selection())

    def _collect_data(self) -> dict:
        return {
            "book_code": self.book_code_entry.get().strip(),
            "title": self.title_entry.get().strip(),
            "author": self.author_entry.get().strip(),
            "category": self.category_entry.get().strip(),
            "publisher": self.publisher_entry.get().strip(),
            "isbn": self.isbn_entry.get().strip(),
            "quantity": self.quantity_entry.get().strip(),
            "shelf_location": self.shelf_entry.get().strip(),
        }

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
        try:
            quantity = int(data["quantity"])
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Validation Error", "Quantity must be a positive whole number."
            )
            return False
        return True

    def add_book(self) -> None:
        data = self._collect_data()
        if not self._validate(data):
            return
        try:
            self.db.add_book(data)
            messagebox.showinfo("Success", "Book added successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def update_book(self) -> None:
        if self.selected_book_id is None:
            messagebox.showwarning("Selection Required", "Select a book to update.")
            return
        data = self._collect_data()
        if not self._validate(data):
            return
        try:
            self.db.update_book(self.selected_book_id, data)
            messagebox.showinfo("Success", "Book updated successfully.")
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_book(self) -> None:
        if self.selected_book_id is None:
            messagebox.showwarning("Selection Required", "Select a book to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected book?"):
            return
        try:
            self.db.delete_book(self.selected_book_id)
            messagebox.showinfo("Success", "Book deleted successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

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
                    book["shelf_location"],
                    book["added_date"],
                )
                for book in books
            ],
        )

    def refresh_data(self) -> None:
        self._set_book_code()
        self.load_data()

    def sort_by(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self.load_data()

    def on_select(self, event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        selected = self.db.get_book_by_code(values[0])
        if not selected:
            return
        self.selected_book_id = selected["id"]
        self.book_code_entry.configure(state="normal")
        self.clear_entries(
            self.book_code_entry,
            self.title_entry,
            self.author_entry,
            self.category_entry,
            self.publisher_entry,
            self.isbn_entry,
            self.quantity_entry,
            self.shelf_entry,
        )
        self.book_code_entry.insert(0, selected["book_code"])
        self.book_code_entry.configure(state="readonly")
        self.title_entry.insert(0, selected["title"])
        self.author_entry.insert(0, selected["author"])
        self.category_entry.insert(0, selected["category"])
        self.publisher_entry.insert(0, selected["publisher"])
        self.isbn_entry.insert(0, selected["isbn"])
        self.quantity_entry.insert(0, str(selected["quantity"]))
        self.shelf_entry.insert(0, selected["shelf_location"])
