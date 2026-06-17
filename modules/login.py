from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from PIL import Image

try:
    from PIL import ImageTk
except Exception:  # pragma: no cover - optional GUI dependency
    ImageTk = None

from modules.base import COLORS, FONTS


class LoginFrame(tk.Frame):
    """Authentication screen for the application."""

    def __init__(self, parent: tk.Widget, app) -> None:
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self._logo_image = None
        self._build_ui()

    def _build_ui(self) -> None:
        wrapper = tk.Frame(self, bg=COLORS["bg"])
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(wrapper, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground="#22314f")
        card.grid(row=0, column=0, sticky="nsew")

        inner = tk.Frame(card, bg=COLORS["panel"], padx=36, pady=32)
        inner.pack(fill="both", expand=True)

        logo_frame = tk.Frame(inner, bg=COLORS["panel"])
        logo_frame.pack(pady=(0, 16))
        self._add_logo(logo_frame)

        title = tk.Label(
            inner,
            text="Library Management System",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=("Segoe UI", 20, "bold"),
        )
        title.pack()

        subtitle = tk.Label(
            inner,
            text="Sign in to manage books, members, issues, and reports.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
        )
        subtitle.pack(pady=(6, 20))

        form = tk.Frame(inner, bg=COLORS["panel"])
        form.pack(fill="x")

        username_label = tk.Label(form, text="Username", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["body"])
        username_label.grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.username_entry = tk.Entry(form, width=32, font=FONTS["body"], relief="flat")
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        password_label = tk.Label(form, text="Password", bg=COLORS["panel"], fg=COLORS["text"], font=FONTS["body"])
        password_label.grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.password_entry = tk.Entry(form, width=32, show="*", font=FONTS["body"], relief="flat")
        self.password_entry.grid(row=3, column=0, sticky="ew", pady=(0, 20))

        login_button = tk.Button(
            form,
            text="Login",
            command=self._attempt_login,
            bg=COLORS["primary"],
            fg="white",
            activebackground=COLORS["primary_dark"],
            activeforeground="white",
            relief="flat",
            font=FONTS["button"],
            padx=16,
            pady=10,
        )
        login_button.grid(row=4, column=0, sticky="ew")

        hint = tk.Label(
            inner,
            text="Default Admin: admin / admin123",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["subtitle"],
        )
        hint.pack(pady=(18, 0))

        form.columnconfigure(0, weight=1)

        self.username_entry.insert(0, "admin")
        self.username_entry.focus_set()
        self.password_entry.bind("<Return>", lambda event: self._attempt_login())
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus_set())

    def _add_logo(self, parent: tk.Widget) -> None:
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
        if logo_path.exists() and ImageTk is not None:
            try:
                image = Image.open(logo_path).convert("RGBA")
                image = image.resize((96, 96))
                self._logo_image = ImageTk.PhotoImage(image)
                label = tk.Label(parent, image=self._logo_image, bg=COLORS["panel"])
                label.pack()
                return
            except Exception:
                pass

        fallback = tk.Canvas(parent, width=96, height=96, bg=COLORS["panel"], highlightthickness=0)
        fallback.create_oval(8, 8, 88, 88, fill=COLORS["primary"], outline="")
        fallback.create_text(48, 48, text="LM", fill="white", font=("Segoe UI", 24, "bold"))
        fallback.pack()

    def _attempt_login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Login Required", "Please enter both username and password.")
            return

        if self.app.handle_login(username, password):
            return

        messagebox.showerror("Login Failed", "Invalid username or password.")
