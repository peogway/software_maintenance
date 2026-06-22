from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from modules.base import BaseModuleFrame, COLORS, FONTS


class SettingsFrame(BaseModuleFrame):
    """Library configuration, account security, and database backup tools."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.library_name_entry = None
        self.address_text = None
        self.phone_entry = None
        self.email_entry = None
        self.current_password_entry = None
        self.new_password_entry = None
        self.confirm_password_entry = None
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Settings",
            "Manage library information, change passwords, and protect the database with backups.",
        )

        wrapper = tk.Frame(self, bg=COLORS["bg"])
        wrapper.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        left = self.build_panel(wrapper)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        left.configure(padx=16, pady=16)

        right = self.build_panel(wrapper)
        right.pack(side="right", fill="both", expand=True)
        right.configure(padx=16, pady=16)

        tk.Label(
            left,
            text="Library Information",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).pack(anchor="w", pady=(0, 12))

        form = tk.Frame(left, bg=COLORS["panel"])
        form.pack(fill="both", expand=True)
        self.library_name_entry = self.labeled_entry(
            form, "Library Name", 0, 0, width=36
        )
        self.address_text = self.labeled_text(form, "Address", 2, 0, height=5)
        self.phone_entry = self.labeled_entry(form, "Phone", 4, 0, width=36)
        self.email_entry = self.labeled_entry(form, "Email", 6, 0, width=36)

        button_row = tk.Frame(form, bg=COLORS["panel"])
        button_row.grid(row=8, column=0, sticky="ew", padx=8, pady=(10, 0))
        button_row.columnconfigure((0, 1), weight=1)
        self.build_button(
            button_row, "Save Library Info", self.save_library_info, COLORS["primary"]
        ).grid(row=0, column=0, sticky="ew", padx=4)

        self.build_button(
            button_row, "Backup Database", self.backup_database, COLORS["success"]
        ).grid(row=0, column=1, sticky="ew", padx=4)

        tk.Label(
            right,
            text="Security & Restore",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).pack(anchor="w", pady=(0, 12), padx=2)

        security = tk.Frame(right, bg=COLORS["panel"])
        security.pack(fill="both", expand=True)

        self.current_password_entry = self.labeled_entry(
            security, "Current Password", 0, 0, width=36, show="*"
        )
        self.new_password_entry = self.labeled_entry(
            security, "New Password", 2, 0, width=36, show="*"
        )
        self.confirm_password_entry = self.labeled_entry(
            security, "Confirm Password", 4, 0, width=36, show="*"
        )

        security_buttons = tk.Frame(security, bg=COLORS["panel"])
        security_buttons.grid(row=6, column=0, sticky="ew", padx=8, pady=(10, 0))
        security_buttons.columnconfigure((0, 1), weight=1)

        self.build_button(
            security_buttons, "Change Password", self.change_password, COLORS["warning"]
        ).grid(row=0, column=0, sticky="ew", padx=4)

        self.build_button(
            security_buttons,
            "Restore Database",
            self.restore_database,
            COLORS["danger"],
        ).grid(row=0, column=1, sticky="ew", padx=4)

        note = tk.Label(
            right,
            text="Backups are copied into the backup folder inside the project directory.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
            wraplength=380,
            justify="left",
        )
        note.pack(anchor="w", padx=8, pady=(18, 0))

        form.columnconfigure(0, weight=1)
        security.columnconfigure(0, weight=1)

    def refresh_data(self) -> None:
        settings = self.db.get_library_settings()
        self.clear_entries(
            self.library_name_entry,
            self.address_text,
            self.phone_entry,
            self.email_entry,
            self.current_password_entry,
            self.new_password_entry,
            self.confirm_password_entry,
        )
        self.library_name_entry.insert(0, settings.get("library_name", ""))
        self.address_text.insert("1.0", settings.get("address", ""))
        self.phone_entry.insert(0, settings.get("phone", ""))
        self.email_entry.insert(0, settings.get("email", ""))

    def save_library_info(self) -> None:
        def save_library_info_flow():
            self.db.update_library_settings(
                {
                    "library_name": self.library_name_entry.get().strip(),
                    "address": self.address_text.get("1.0", tk.END).strip(),
                    "phone": self.phone_entry.get().strip(),
                    "email": self.email_entry.get().strip(),
                }
            )
            self.app.refresh_header()

        success = self.safe_fn(
            save_library_info_flow,
            success_msg="Library information updated successfully.",
        )

    def change_password(self) -> None:
        current_password = self.current_password_entry.get().strip()
        new_password = self.new_password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        if not current_password or not new_password or not confirm_password:
            messagebox.showwarning(
                "Validation Error", "All password fields are required."
            )
            return
        if new_password != confirm_password:
            messagebox.showwarning(
                "Validation Error", "New password and confirmation do not match."
            )
            return
        username = self.app.current_user["username"]
        if not self.db.change_password(username, current_password, new_password):
            messagebox.showerror("Error", "Current password is incorrect.")
            return
        messagebox.showinfo("Success", "Password changed successfully.")
        self.clear_entries(
            self.current_password_entry,
            self.new_password_entry,
            self.confirm_password_entry,
        )

    def backup_database(self) -> None:
        try:
            backup_path = self.db.backup_database()
            messagebox.showinfo(
                "Backup Complete", f"Database backed up to:\n{backup_path}"
            )
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc))

    def restore_database(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select database backup",
            filetypes=[("SQLite Database", "*.db"), ("All files", "*.*")],
            initialdir=str(self.db.backup_dir),
        )
        if not file_path:
            return
        if not messagebox.askyesno(
            "Confirm Restore",
            "Restore the database from this backup? Current data will be replaced.",
        ):
            return

        def restore_database_flow(file_path):
            self.db.restore_database(file_path)
            self.app.refresh_header()

        success = self.safe_fn(
            lambda: restore_database_flow(file_path),
            success_msg="Database restored successfully.",
            refresh_data=True,
        )
