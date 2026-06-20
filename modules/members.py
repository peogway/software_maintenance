from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class MembersFrame(BaseModuleFrame):
    """Member management screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_member_id = None
        self.search_field_var = tk.StringVar(value="name")
        self.search_text_var = tk.StringVar()
        self.sort_column = "name"
        self.sort_ascending = True
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Member Management",
            "Register members, update records, and search by name, code, or phone.",
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
            values=["name", "member_code", "phone"],
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

        left = tk.Frame(
            content,
            bg=COLORS["panel"],
            bd=0,
            highlightthickness=1,
            highlightbackground="#22314f",
        )
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=440)
        left.pack_propagate(False)

        form = tk.Frame(left, bg=COLORS["panel"], padx=10, pady=10)
        form.pack(fill="both", expand=True)

        self.member_code_entry = self.labeled_entry(
            form, "Member Code", 0, 0, readonly=True
        )
        self.name_entry = self.labeled_entry(form, "Name", 0, 1)
        self.email_entry = self.labeled_entry(form, "Email", 2, 0)
        self.phone_entry = self.labeled_entry(form, "Phone", 2, 1)
        self.address_text = self.labeled_text(form, "Address", 4, 0, height=5)
        self.address_text.grid(columnspan=2)

        action_row = tk.Frame(form, bg=COLORS["panel"])
        action_row.grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 0)
        )
        action_row.columnconfigure((0, 1, 2, 3), weight=1)

        self.create_button(action_row, "Add", self.add_member, COLORS["success"]).grid(
            row=0, column=0, sticky="ew", padx=3
        )

        self.create_button(
            action_row, "Update", self.update_member, COLORS["warning"]
        ).grid(row=0, column=1, sticky="ew", padx=3)

        self.create_button(
            action_row, "Delete", self.delete_member, COLORS["danger"]
        ).grid(row=0, column=2, sticky="ew", padx=3)

        self.create_button(
            action_row, "Clear", self.clear_form, COLORS["secondary"]
        ).grid(row=0, column=3, sticky="ew", padx=3)

        right = tk.Frame(
            content,
            bg=COLORS["panel"],
            bd=0,
            highlightthickness=1,
            highlightbackground="#22314f",
        )
        right.pack(side="right", fill="both", expand=True)

        table_wrap = tk.Frame(right, bg=COLORS["panel"], padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = ["member_code", "name", "email", "phone", "address", "join_date"]
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", selectmode="browse"
        )
        widths = {
            "member_code": 100,
            "name": 170,
            "email": 180,
            "phone": 130,
            "address": 250,
            "join_date": 120,
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
        self.search_field_var.set("name")
        self.search_text_var.set("")
        self.load_data()

    def _set_member_code(self) -> None:
        code = self.db.generate_member_code()
        self.member_code_entry.configure(state="normal")
        self.member_code_entry.delete(0, tk.END)
        self.member_code_entry.insert(0, code)
        self.member_code_entry.configure(state="readonly")

    def clear_form(self) -> None:
        self.selected_member_id = None
        self.clear_entries(
            self.member_code_entry,
            self.name_entry,
            self.email_entry,
            self.phone_entry,
            self.address_text,
        )
        self._set_member_code()
        self.tree.selection_remove(self.tree.selection())

    def _collect_data(self) -> dict:
        return {
            "member_code": self.member_code_entry.get().strip(),
            "name": self.name_entry.get().strip(),
            "email": self.email_entry.get().strip(),
            "phone": self.phone_entry.get().strip(),
            "address": self.address_text.get("1.0", tk.END).strip(),
        }

    def _validate(self, data: dict) -> bool:
        if not data["name"]:
            messagebox.showwarning("Validation Error", "Name is required.")
            return False
        if not data["address"]:
            messagebox.showwarning("Validation Error", "Address is required.")
            return False
        return True

    def add_member(self) -> None:
        data = self._collect_data()
        if not self._validate(data):
            return
        try:
            self.db.add_member(data)
            messagebox.showinfo("Success", "Member added successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def update_member(self) -> None:
        if self.selected_member_id is None:
            messagebox.showwarning("Selection Required", "Select a member to update.")
            return
        data = self._collect_data()
        if not self._validate(data):
            return
        try:
            self.db.update_member(self.selected_member_id, data)
            messagebox.showinfo("Success", "Member updated successfully.")
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_member(self) -> None:
        if self.selected_member_id is None:
            messagebox.showwarning("Selection Required", "Select a member to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected member?"):
            return
        try:
            self.db.delete_member(self.selected_member_id)
            messagebox.showinfo("Success", "Member deleted successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def load_data(self) -> None:
        search_text = self.search_text_var.get().strip()
        field = self.search_field_var.get().strip() or "name"
        members = self.db.fetch_members(
            search_text, field, self.sort_column, self.sort_ascending
        )
        self.fill_treeview(
            self.tree,
            [
                (
                    member["member_code"],
                    member["name"],
                    member["email"] or "",
                    member["phone"] or "",
                    member["address"],
                    member["join_date"],
                )
                for member in members
            ],
        )

    def refresh_data(self) -> None:
        self._set_member_code()
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
        selected = self.db.get_member_by_code(values[0])
        if not selected:
            return
        self.selected_member_id = selected["id"]
        self.member_code_entry.configure(state="normal")
        self.clear_entries(
            self.member_code_entry,
            self.name_entry,
            self.email_entry,
            self.phone_entry,
            self.address_text,
        )
        self.member_code_entry.insert(0, selected["member_code"])
        self.member_code_entry.configure(state="readonly")
        self.name_entry.insert(0, selected["name"])
        self.email_entry.insert(0, selected["email"] or "")
        self.phone_entry.insert(0, selected["phone"] or "")
        self.address_text.insert("1.0", selected["address"])
