from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class MembersFrame(BaseModuleFrame):
    """Member management screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_id = None
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

        self.build_button(search_bar, "Search", self.load_data, COLORS["primary"]).grid(
            row=0, column=4, padx=6
        )

        self.build_button(
            search_bar, "Reset", lambda: self._reset_search("name"), COLORS["secondary"]
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

        self.code_entry = self.labeled_entry(form, "Member Code", 0, 0, readonly=True)
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

        self.build_button(action_row, "Add", self.add_member, COLORS["success"]).grid(
            row=0, column=0, sticky="ew", padx=3
        )

        self.build_button(
            action_row, "Update", self.update_member, COLORS["warning"]
        ).grid(row=0, column=1, sticky="ew", padx=3)

        self.build_button(
            action_row, "Delete", self.delete_member, COLORS["danger"]
        ).grid(row=0, column=2, sticky="ew", padx=3)

        self.build_button(
            action_row, "Clear", self.clear_form, COLORS["secondary"]
        ).grid(row=0, column=3, sticky="ew", padx=3)

        right = self.build_panel(content)
        right.pack(side="right", fill="both", expand=True)

        table_wrap = tk.Frame(right, bg=COLORS["panel"], padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = ["member_code", "name", "email", "phone", "address", "join_date"]

        widths = {
            "member_code": 100,
            "name": 170,
            "email": 180,
            "phone": 130,
            "address": 250,
            "join_date": 120,
        }
        self.tree, self.scrollbar = self.build_table(table_wrap, columns, widths)

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self.form_fields = {
            "member_code": self.code_entry,
            "name": self.name_entry,
            "email": self.email_entry,
            "phone": self.phone_entry,
            "address": self.address_text,
        }

    def _get_code(self) -> str:
        return self.db.generate_member_code()

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

        success = self.safe_fn(
            lambda: self.db.add_member(data),
            success_msg="Member added successfully.",
            clear_form=True,
            load_data=True,
        )

    def update_member(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Selection Required", "Select a member to update.")
            return
        data = self._collect_data()
        if not self._validate(data):
            return

        success = self.safe_fn(
            lambda: self.db.update_member(self.selected_id, data),
            success_msg="Member updated successfully.",
            load_data=True,
        )

    def delete_member(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Selection Required", "Select a member to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected member?"):
            return

        success = self.safe_fn(
            lambda: self.db.delete_member(self.selected_id),
            success_msg="Member deleted successfully.",
            clear_form=True,
            load_data=True,
        )

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

    def on_select(self, event) -> None:
        super().on_select(self.db.get_member_by_code, code_entry=True)
