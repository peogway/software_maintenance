from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Type

from modules.base import COLORS, FONTS
from modules.books import BooksFrame
from modules.dashboard import DashboardFrame
from modules.issue_books import IssueBooksFrame
from modules.login import LoginFrame
from modules.members import MembersFrame
from modules.reports import ReportsFrame
from modules.settings import SettingsFrame
from modules.users import UsersFrame
from modules.database import LibraryDatabase
from modules.reserve_books import ReserveBookFrame


class LibraryApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Library Management System")
        self.geometry("1400x800")
        self.minsize(1200, 720)
        self.configure(bg=COLORS["bg"])

        self.db = LibraryDatabase()
        self.current_user = None
        self.shell = None
        self.login_frame = None

        self._configure_styles()

        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)

        self.show_login()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("Card.TFrame", background=COLORS["card"])
        style.configure(
            "TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=FONTS["body"],
        )
        style.configure("TButton", font=FONTS["button"], padding=(12, 8))
        style.configure(
            "Primary.TButton", background=COLORS["primary"], foreground="white"
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", COLORS["primary_dark"]),
                ("disabled", COLORS["secondary"]),
            ],
            foreground=[("disabled", "#cbd5e1")],
        )
        style.configure(
            "Secondary.TButton", background=COLORS["secondary"], foreground="white"
        )
        style.map("Secondary.TButton", background=[("active", "#475569")])
        style.configure(
            "Treeview",
            background=COLORS["table_bg"],
            foreground="#0f172a",
            fieldbackground=COLORS["table_bg"],
            rowheight=28,
            bordercolor="#cbd5e1",
            lightcolor="#cbd5e1",
            darkcolor="#cbd5e1",
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["panel_alt"],
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map("Treeview", background=[("selected", COLORS["accent"])])
        style.configure("TCombobox", padding=4, foreground="#0f172a")
        style.configure("TEntry", padding=4)

    def clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def show_login(self) -> None:
        self.clear_container()
        self.shell = None
        self.current_user = None
        self.login_frame = LoginFrame(self.container, self)
        self.login_frame.pack(fill="both", expand=True)

    def show_shell(self) -> None:
        self.clear_container()
        self.login_frame = None
        self.shell = ShellFrame(self.container, self)
        self.shell.pack(fill="both", expand=True)
        self.shell.show_dashboard()

    def handle_login(self, username: str, password: str) -> bool:
        user = self.db.authenticate_user(username, password)
        if not user:
            return False
        self.current_user = user
        self.show_shell()
        return True

    def logout(self) -> None:
        if messagebox.askyesno("Logout", "Do you want to log out now?"):
            self.show_login()

    def refresh_header(self) -> None:
        if self.shell:
            self.shell.refresh_header()


class ShellFrame(tk.Frame):
    """Application shell with sidebar navigation and header."""

    def __init__(self, parent: tk.Widget, app: LibraryApp) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.current_module = None
        self.modules: Dict[str, Type[tk.Frame]] = {
            "dashboard": DashboardFrame,
            "books": BooksFrame,
            "members": MembersFrame,
            "issues": IssueBooksFrame,
            "reserves": ReserveBookFrame,
            "reports": ReportsFrame,
            "settings": SettingsFrame,
            "users": UsersFrame,
        }

        self.sidebar = tk.Frame(self, bg=COLORS["panel"], width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.main_area = tk.Frame(self, bg=COLORS["bg"])
        self.main_area.pack(side="right", fill="both", expand=True)

        self.header = tk.Frame(self.main_area, bg=COLORS["panel_alt"], height=76)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)

        self.content = tk.Frame(self.main_area, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True)

        self._build_sidebar()
        self.refresh_header()

    def _build_sidebar(self) -> None:
        top = tk.Frame(self.sidebar, bg=COLORS["panel"], pady=22)
        top.pack(fill="x")

        self.logo_label = tk.Label(
            top,
            text="Library IMS",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        )
        self.logo_label.pack(anchor="w", padx=22)

        subtitle = tk.Label(
            top,
            text="Offline desktop admin panel",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
        )
        subtitle.pack(anchor="w", padx=22, pady=(4, 0))

        button_specs = [
            ("Dashboard", "dashboard"),
            ("Books", "books"),
            ("Members", "members"),
            ("Issue Books", "issues"),
            ("Reserve Books", "reserves"),
            ("Reports", "reports"),
            ("Settings", "settings"),
        ]

        if self.app.current_user and self.app.current_user.get("role") == "admin":
            button_specs.insert(5, ("Users", "users"))

        nav = tk.Frame(self.sidebar, bg=COLORS["panel"], pady=12)
        nav.pack(fill="both", expand=True)

        for text, key in button_specs:
            button = tk.Button(
                nav,
                text=text,
                command=lambda module_key=key: self.show_module(module_key),
                bg=COLORS["panel"],
                fg=COLORS["text"],
                activebackground=COLORS["primary"],
                activeforeground="white",
                relief="flat",
                anchor="w",
                padx=18,
                pady=12,
                font=FONTS["button"],
            )
            button.pack(fill="x", padx=12, pady=4)

        logout_button = tk.Button(
            self.sidebar,
            text="Logout",
            command=self.app.logout,
            bg=COLORS["danger"],
            fg="white",
            activebackground="#dc2626",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=12,
            font=FONTS["button"],
        )
        logout_button.pack(fill="x", padx=12, pady=(0, 16))

    def refresh_header(self) -> None:
        for child in self.header.winfo_children():
            child.destroy()

        settings = self.app.db.get_library_settings()
        title_text = settings.get("library_name") or "Library Management System"
        info_text = f"Logged in as {self.app.current_user['username']} ({self.app.current_user['role']})"

        left = tk.Frame(self.header, bg=COLORS["panel_alt"])
        left.pack(side="left", fill="y", padx=22)

        title = tk.Label(
            left,
            text=title_text,
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            font=("Segoe UI", 18, "bold"),
        )
        title.pack(anchor="w", pady=(14, 0))

        subtitle = tk.Label(
            left,
            text=info_text,
            bg=COLORS["panel_alt"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
        )
        subtitle.pack(anchor="w", pady=(4, 0))

    def show_module(self, module_key: str) -> None:
        if module_key == "users" and self.app.current_user.get("role") != "admin":
            messagebox.showwarning(
                "Access Denied", "Only admin users can manage application accounts."
            )
            return
        if self.current_module is not None:
            self.current_module.destroy()

        module_class = self.modules[module_key]
        self.current_module = module_class(self.content, self.app, self.app.db)
        self.current_module.pack(fill="both", expand=True)
        if hasattr(self.current_module, "refresh_data"):
            self.current_module.refresh_data()
        elif hasattr(self.current_module, "load_data"):
            self.current_module.load_data()

    def show_dashboard(self) -> None:
        self.show_module("dashboard")


if __name__ == "__main__":
    app = LibraryApp()
    app.mainloop()
