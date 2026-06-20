from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class UsersFrame(BaseModuleFrame):
    """Admin user management screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_user_id = None
        self.search_field_var = tk.StringVar(value="username")
        self.search_text_var = tk.StringVar()
        self.sort_column = "created_at"
        self.sort_ascending = False
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "User Management",
            "Create staff accounts, update roles, and keep access control inside the app.",
        )

        controls = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=14)
        controls.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(
            controls,
            text="Search By",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=0, column=0, sticky="w", padx=6)
        self.search_field = ttk.Combobox(
            controls,
            textvariable=self.search_field_var,
            values=["username", "role", "created_at"],
            state="readonly",
            width=16,
        )
        self.search_field.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(
            controls,
            text="Keyword",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=0, column=2, sticky="w", padx=6)
        self.search_entry = tk.Entry(
            controls, textvariable=self.search_text_var, width=28, relief="flat"
        )
        self.search_entry.grid(row=0, column=3, padx=6, pady=6)

        self.create_button(controls, "Search", self.load_data, COLORS["primary"]).grid(
            row=0, column=4, padx=6
        )

        self.create_button(
            controls, "Reset", self._reset_search, COLORS["secondary"]
        ).grid(row=0, column=5, padx=6)

        controls.columnconfigure(6, weight=1)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        left = self.create_panel(content)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.configure(width=440)
        left.pack_propagate(False)

        form = tk.Frame(left, bg=COLORS["panel"], padx=10, pady=10)
        form.pack(fill="both", expand=True)

        self.username_entry = self.labeled_entry(form, "Username", 0, 0)
        self.password_entry = self.labeled_entry(form, "Password", 2, 0, show="*")
        self.confirm_password_entry = self.labeled_entry(
            form, "Confirm Password", 4, 0, show="*"
        )
        self.role_var = tk.StringVar(value="staff")
        role_label = tk.Label(
            form, text="Role", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["body"]
        )
        role_label.grid(row=6, column=0, sticky="w", padx=8, pady=(8, 3))
        self.role_combo = ttk.Combobox(
            form,
            textvariable=self.role_var,
            values=["admin", "staff"],
            state="readonly",
        )
        self.role_combo.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 8))

        actions = tk.Frame(form, bg=COLORS["panel"])
        actions.grid(row=8, column=0, sticky="ew", padx=8, pady=(12, 0))
        actions.columnconfigure((0, 1, 2, 3), weight=1)

        self.create_button(actions, "Add", self.add_user, COLORS["success"]).grid(
            row=0, column=0, sticky="ew", padx=3
        )

        self.create_button(actions, "Update", self.update_user, COLORS["warning"]).grid(
            row=0, column=1, sticky="ew", padx=3
        )

        self.create_button(actions, "Delete", self.delete_user, COLORS["danger"]).grid(
            row=0, column=2, sticky="ew", padx=3
        )

        self.create_button(actions, "Clear", self.clear_form, COLORS["secondary"]).grid(
            row=0, column=3, sticky="ew", padx=3
        )

        note = tk.Label(
            form,
            text="Leave password blank when updating a user if you do not want to change it.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
            wraplength=360,
            justify="left",
        )
        note.grid(row=9, column=0, sticky="w", padx=8, pady=(14, 0))

        right = self.create_panel(content)
        right.pack(side="right", fill="both", expand=True)

        table_wrap = tk.Frame(right, bg=COLORS["panel"], padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = ["id", "username", "role", "created_at"]
        self.tree = ttk.Treeview(
            table_wrap, columns=columns, show="headings", selectmode="browse"
        )
        widths = {"id": 70, "username": 180, "role": 100, "created_at": 160}
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

    def _reset_search(self) -> None:
        self.search_field_var.set("username")
        self.search_text_var.set("")
        self.load_data()

    def clear_form(self) -> None:
        self.selected_user_id = None
        self.clear_entries(
            self.username_entry,
            self.password_entry,
            self.confirm_password_entry,
        )
        self.role_var.set("staff")
        self.tree.selection_remove(self.tree.selection())

    def _collect_data(self) -> dict:
        return {
            "username": self.username_entry.get().strip(),
            "password": self.password_entry.get().strip(),
            "confirm_password": self.confirm_password_entry.get().strip(),
            "role": self.role_var.get().strip(),
        }

    def _validate_add(self, data: dict) -> bool:
        if not data["username"]:
            messagebox.showwarning("Validation Error", "Username is required.")
            return False
        if not data["password"]:
            messagebox.showwarning("Validation Error", "Password is required.")
            return False
        if data["password"] != data["confirm_password"]:
            messagebox.showwarning(
                "Validation Error", "Password confirmation does not match."
            )
            return False
        return True

    def _validate_update(self, data: dict) -> bool:
        if not data["username"]:
            messagebox.showwarning("Validation Error", "Username is required.")
            return False
        if data["password"] and data["password"] != data["confirm_password"]:
            messagebox.showwarning(
                "Validation Error", "Password confirmation does not match."
            )
            return False
        return True

    def add_user(self) -> None:
        data = self._collect_data()
        if not self._validate_add(data):
            return
        try:
            self.db.create_user(data["username"], data["password"], data["role"])
            messagebox.showinfo("Success", "User added successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def update_user(self) -> None:
        if self.selected_user_id is None:
            messagebox.showwarning("Selection Required", "Select a user to update.")
            return
        data = self._collect_data()
        if not self._validate_update(data):
            return
        try:
            self.db.update_user(
                self.selected_user_id,
                data["username"],
                data["role"],
                data["password"] or None,
            )
            messagebox.showinfo("Success", "User updated successfully.")
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_user(self) -> None:
        if self.selected_user_id is None:
            messagebox.showwarning("Selection Required", "Select a user to delete.")
            return
        if (
            self.app.current_user
            and self.app.current_user["id"] == self.selected_user_id
        ):
            messagebox.showwarning(
                "Action Not Allowed",
                "You cannot delete the account you are currently logged into.",
            )
            return
        if not messagebox.askyesno("Confirm Delete", "Delete the selected user?"):
            return
        try:
            self.db.delete_user(self.selected_user_id)
            messagebox.showinfo("Success", "User deleted successfully.")
            self.clear_form()
            self.load_data()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def load_data(self) -> None:
        users = self.db.fetch_users(
            self.search_text_var.get(),
            self.search_field_var.get(),
            self.sort_column,
            self.sort_ascending,
        )
        self.fill_treeview(
            self.tree,
            [
                (user["id"], user["username"], user["role"], user["created_at"])
                for user in users
            ],
        )

    def refresh_data(self) -> None:
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
        user = self.db.get_user_by_id(int(values[0]))
        if not user:
            return
        self.selected_user_id = user["id"]
        self.clear_entries(
            self.username_entry, self.password_entry, self.confirm_password_entry
        )
        self.username_entry.insert(0, user["username"])
        self.role_var.set(user["role"])
