from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from modules.base import BaseModuleFrame, COLORS, FONTS


class ReportsFrame(BaseModuleFrame):
    """Reporting and export screen."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.report_var = tk.StringVar(value="Available Books")
        self.current_columns = []
        self.current_rows = []
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.build_heading(
            "Reports",
            "Generate availability, issue, overdue, member, and fine reports. Export any report to CSV.",
        )

        controls = tk.Frame(self, bg=COLORS["panel"], padx=18, pady=14)
        controls.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(
            controls,
            text="Report Type",
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=FONTS["body"],
        ).grid(row=0, column=0, sticky="w", padx=6)
        self.report_combo = ttk.Combobox(
            controls,
            textvariable=self.report_var,
            values=[
                "Available Books",
                "Issued Books",
                "Overdue Books",
                "Member Report",
                "Fine Report",
            ],
            state="readonly",
            width=22,
        )
        self.report_combo.grid(row=0, column=1, padx=6)

        self.create_button(
            controls, "Load Report", self.load_report, COLORS["primary"]
        ).grid(row=0, column=2, padx=6)

        self.create_button(
            controls, "Export CSV", self.export_csv, COLORS["success"]
        ).grid(row=0, column=3, padx=6)

        self.summary_label = tk.Label(
            controls,
            text="0 records",
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=FONTS["body"],
        )
        self.summary_label.grid(row=0, column=4, padx=12, sticky="e")
        controls.columnconfigure(4, weight=1)

        table_frame = self.create_panel(self)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        inner = tk.Frame(table_frame, bg=COLORS["panel"], padx=10, pady=10)
        inner.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(inner, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _report_definitions(self) -> dict:
        return {
            "Available Books": {
                "columns": [
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
                ],
                "loader": self.db.report_available_books,
            },
            "Issued Books": {
                "columns": [
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
                ],
                "loader": self.db.report_issued_books,
            },
            "Overdue Books": {
                "columns": [
                    "id",
                    "book_code",
                    "title",
                    "member_code",
                    "member_name",
                    "issue_date",
                    "due_date",
                    "status",
                    "fine_amount",
                ],
                "loader": self.db.report_overdue_books,
            },
            "Member Report": {
                "columns": [
                    "member_code",
                    "name",
                    "email",
                    "phone",
                    "address",
                    "join_date",
                ],
                "loader": self.db.report_members,
            },
            "Fine Report": {
                "columns": [
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
                ],
                "loader": self.db.report_fines,
            },
        }

    def _format_row(self, report_name: str, row: dict) -> tuple:
        if report_name == "Available Books":
            return (
                row["book_code"],
                row["title"],
                row["author"],
                row["category"],
                row["publisher"],
                row["isbn"],
                row["quantity"],
                row["available_quantity"],
                row["shelf_location"],
                row["added_date"],
            )
        if report_name in {"Issued Books", "Fine Report"}:
            return (
                row["id"],
                row["book_code"],
                row["title"],
                row["member_code"],
                row["member_name"],
                row["issue_date"],
                row["due_date"],
                row["return_date"] or "",
                row["status"],
                f"Tk {row['fine_amount']:.2f}",
            )
        if report_name == "Overdue Books":
            return (
                row["id"],
                row["book_code"],
                row["title"],
                row["member_code"],
                row["member_name"],
                row["issue_date"],
                row["due_date"],
                row["status"],
                f"Tk {row['fine_amount']:.2f}",
            )
        if report_name == "Member Report":
            return (
                row["member_code"],
                row["name"],
                row["email"] or "",
                row["phone"] or "",
                row["address"],
                row["join_date"],
            )
        return (
            row["member_code"],
            row["name"],
            row["email"] or "",
            row["phone"] or "",
            row["address"],
            row["join_date"],
        )

    def _configure_tree(self, columns: list[str]) -> None:
        self.tree["columns"] = columns
        for item in self.tree.get_children():
            self.tree.delete(item)
        for column in columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=140, anchor="center", stretch=True)

    def load_report(self) -> None:
        report_name = self.report_var.get()
        report_def = self._report_definitions()[report_name]
        self.current_columns = report_def["columns"]
        rows = report_def["loader"]()
        self.current_rows = [self._format_row(report_name, row) for row in rows]
        self._configure_tree(self.current_columns)
        for row in self.current_rows:
            self.tree.insert("", "end", values=row)
        self.summary_label.configure(text=f"{len(self.current_rows)} records")

    def refresh_data(self) -> None:
        self.load_report()

    def export_csv(self) -> None:
        if not self.current_rows:
            messagebox.showwarning("No Data", "Load a report before exporting.")
            return
        report_name = self.report_var.get().lower().replace(" ", "_")
        file_path = filedialog.asksaveasfilename(
            title="Export report to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"{report_name}.csv",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)
                writer.writerow(self.current_columns)
                writer.writerows(self.current_rows)
            messagebox.showinfo("Export Complete", f"Report exported to {file_path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))
