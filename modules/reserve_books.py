from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class ReserveBookFrame(BaseModuleFrame):
    """Issue and return book workflow."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.selected_id = None
        self.current_pos = None
        self.cur_book_code = None
        self.cur_status = None
        self.search_field_var = tk.StringVar(value="book_title")
        self.search_text_var = tk.StringVar()
        self.member_options = {}
        self.book_options = {}
        self.member_var = tk.StringVar()
        self.book_var = tk.StringVar()
        self.db.expire_reservations()
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Books Reservation",
        )

        search_bar = tk.Frame(
            self,
            bg=COLORS["panel"],
            padx=18,
            pady=14,
            highlightthickness=1,
            highlightbackground="#22314f",
        )
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
            values=[
                "book_code",
                "book_title",
                "member_code",
                "member_name",
                "status",
            ],
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
            lambda: self._reset_search("book_title"),
            COLORS["secondary"],
        ).grid(row=0, column=5, padx=6)

        search_bar.columnconfigure(6, weight=1)

        top = tk.Frame(self, bg=COLORS["bg"])
        top.pack(fill="x", padx=24, pady=(0, 16))

        reserve_panel = self.build_panel(top)

        reserve_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))
        reserve_panel.configure(padx=18, pady=18)

        tk.Label(
            reserve_panel,
            text="Reserve Book",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        tk.Label(
            reserve_panel,
            text="Member",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=1, column=0, sticky="w", padx=6)
        self.member_combo = ttk.Combobox(
            reserve_panel, textvariable=self.member_var, state="readonly", width=42
        )
        self.member_combo.grid(
            row=2, column=0, sticky="ew", padx=6, pady=(0, 10), columnspan=2
        )

        tk.Label(
            reserve_panel,
            text="Book",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=3, column=0, sticky="w", padx=6)
        self.book_combo = ttk.Combobox(
            reserve_panel, textvariable=self.book_var, state="readonly", width=42
        )
        self.book_combo.grid(
            row=4, column=0, sticky="ew", padx=6, pady=(0, 10), columnspan=2
        )

        self.build_button(
            reserve_panel, "Reserve Book", self.add_reservation, COLORS["primary"]
        ).grid(row=5, column=0, sticky="ew", padx=6, pady=(8, 0))

        return_panel = self.build_panel(top)
        return_panel.pack(side="right", fill="both", expand=True)
        return_panel.configure(padx=18, pady=18)

        tk.Label(
            return_panel,
            text="Operate Reservation",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["heading"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.reserve_id_label = tk.Label(
            return_panel,
            text="Select a reserved record from the table below.",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["body"],
            wraplength=360,
            justify="left",
        )
        self.reserve_id_label.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 14))

        self.build_button(
            return_panel,
            "Issue Book",
            self.issue_book,
            COLORS["success"],
        ).grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 5))

        self.build_button(
            return_panel,
            "Cancel Reservation",
            self.cancel_reservation,
            COLORS["warning"],
        ).grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 15))

        self.build_button(
            return_panel,
            "Move Up",
            self.move_up,
            COLORS["primary"],
        ).grid(row=4, column=0, sticky="ew", padx=6, pady=(0, 5))

        self.build_button(
            return_panel,
            "Move Down",
            self.move_down,
            COLORS["primary"],
        ).grid(row=5, column=0, sticky="ew", padx=6)

        bottom = self.build_panel(self)
        bottom.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        table_wrap = self.build_panel(bottom)
        table_wrap.configure(padx=10, pady=10)
        table_wrap.pack(fill="both", expand=True)

        columns = [
            "id",
            "book_code",
            "title",
            "member_code",
            "member_name",
            "reserved_date",
            "ready_date",
            "expiry_date",
            "queue_pos",
            "status",
        ]

        widths = {
            "id": 60,
            "book_code": 90,
            "title": 180,
            "member_code": 100,
            "member_name": 160,
            "reserved_date": 110,
            "ready_date": 110,
            "expiry_date": 110,
            "queue_pos": 60,
            "status": 90,
        }

        self.tree, self.scrollbar = self.build_table(table_wrap, columns, widths)

        reserve_panel.columnconfigure((0, 1), weight=1)
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
        books = self.db.report_unavailable_books()
        self.book_options = {
            f"{book['book_code']} - {book['title']} (Avail: {book['available_quantity']}, Reserved: {book['reserved_quantity']}))": book[
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

    def add_reservation(self) -> None:
        member_id = self._selected_member_id()
        book_id = self._selected_book_id()
        if member_id is None or book_id is None:
            messagebox.showwarning(
                "Selection Required", "Select both a member and a book."
            )
            return

        success = self.safe_fn(
            lambda: self.db.add_reservation(book_id=book_id, member_id=member_id),
            success_msg="Book reserved successfully.",
            refresh_data=True,
        )

    def issue_book(self) -> None:
        if self.selected_id is None or self.cur_status != "Ready":
            messagebox.showwarning(
                "Selection Required", "Select a Ready reserved record to issue."
            )
            return
        reservation = self.db.get_reservation_by_id(self.selected_id)
        self.safe_fn(
            lambda: self.db.issue_book(
                reservation["book_id"], reservation["member_id"]
            ),
            success_msg="Book issued successfully.",
            refresh_data=True,
        )

    def cancel_reservation(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(
                "Selection Required", "Select a reserved record to return."
            )
            return

        self.safe_fn(
            lambda: self.db.cancel_reservation(self.selected_id),
            load_data=True,
            success_msg="Book added successfully.",
        )

    def move_up(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(
                "Selection Required", "Select a reserved record to return."
            )
            return

        if self.cur_status != "Active":
            messagebox.showwarning(
                "Invalid choice", "Only Active reservation can change queue position"
            )
            return

        self.safe_fn(
            lambda: self.db.change_queue_pos(
                int(self.current_pos), int(self.current_pos) - 1, self.cur_book_code
            ),
            load_data=True,
            success_msg="Reservation moved up successfully.",
        )

    def move_down(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(
                "Selection Required", "Select a reserved record to return."
            )
            return

        if self.cur_status != "Active":
            messagebox.showwarning(
                "Invalid choice", "Only Active reservation can change queue position"
            )
            return

        self.safe_fn(
            lambda: self.db.change_queue_pos(
                int(self.current_pos), int(self.current_pos) + 1, self.cur_book_code
            ),
            load_data=True,
            success_msg="Reservation moved down successfully.",
        )

    def load_data(self) -> None:
        search_text = self.search_text_var.get().strip()
        field = self.search_field_var.get().strip() or "title"
        if field == "book_titile":
            field = "title"
        reservations = self.db.fetch_reservations(
            search_text, field, self.sort_column, self.sort_ascending
        )
        self.fill_treeview(
            self.tree,
            [
                (
                    reservation["id"],
                    reservation["book_code"],
                    reservation["title"],
                    reservation["member_code"],
                    reservation["member_name"],
                    reservation["reserved_date"],
                    reservation["expiry_date"] or "",
                    reservation["ready_date"] or "",
                    reservation["queue_pos"] or "",
                    reservation["status"],
                )
                for reservation in reservations
            ],
        )

    def refresh_data(self) -> None:
        self.selected_id = None
        self._load_member_options()
        self._load_book_options()
        self.load_data()
        self.reserve_id_label.configure(
            text="Select a reserved record from the table below."
        )

    def on_select(self, event) -> None:
        super().on_select(reserve_selection=True)
