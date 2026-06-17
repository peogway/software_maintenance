from __future__ import annotations

import tkinter as tk
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modules.base import BaseModuleFrame, COLORS, FONTS


class DashboardFrame(BaseModuleFrame):
    """Dashboard with summary statistics."""

    def __init__(self, parent: tk.Widget, app, db) -> None:
        super().__init__(parent, app, db)
        self.stat_labels = {}
        self.build_heading(
            "Dashboard",
            "A quick overview of books, members, issues, fines, and overdue activity.",
        )
        self._build_cards()
        self._build_charts()
        self.refresh_data()

    def _build_cards(self) -> None:
        cards_wrap = tk.Frame(self, bg=COLORS["bg"])
        cards_wrap.pack(fill="x", padx=24, pady=(8, 18))

        grid = tk.Frame(cards_wrap, bg=COLORS["bg"])
        grid.pack(fill="x")

        stats = [
            ("Total Books", "total_books", COLORS["primary"]),
            ("Total Members", "total_members", COLORS["accent"]),
            ("Books Issued", "books_issued", COLORS["warning"]),
            ("Books Available", "books_available", COLORS["success"]),
            ("Overdue Books", "overdue_books", COLORS["danger"]),
            ("Total Fines", "total_fines", "#8b5cf6"),
        ]

        for index, (title, key, accent) in enumerate(stats):
            row = index // 3
            column = index % 3
            card_holder = tk.Frame(grid, bg=COLORS["bg"], padx=8, pady=8)
            card_holder.grid(row=row, column=column, sticky="nsew")
            card = self.build_card(card_holder, title, "0", accent)
            card.configure(width=360, height=120)
            card.pack(fill="both", expand=True)
            value_label = card.winfo_children()[-1]
            self.stat_labels[key] = value_label

        for index in range(3):
            grid.columnconfigure(index, weight=1)

    def _build_charts(self) -> None:
        self.charts_wrap = tk.Frame(self, bg=COLORS["bg"])
        self.charts_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(10, 4), facecolor=COLORS["bg"])
        self.fig.tight_layout(pad=4.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.charts_wrap)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self._style_axes(self.ax1)
        self._style_axes(self.ax2)

    def _style_axes(self, ax) -> None:
        ax.set_facecolor(COLORS["bg"])
        ax.tick_params(colors=COLORS["muted"])
        ax.xaxis.label.set_color(COLORS["muted"])
        ax.yaxis.label.set_color(COLORS["muted"])
        ax.title.set_color(COLORS["text"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["panel_alt"])

    def refresh_data(self) -> None:
        stats = self.db.dashboard_stats()
        self.stat_labels["total_books"].configure(text=str(stats["total_books"]))
        self.stat_labels["total_members"].configure(text=str(stats["total_members"]))
        self.stat_labels["books_issued"].configure(text=str(stats["books_issued"]))
        self.stat_labels["books_available"].configure(text=str(stats["books_available"]))
        self.stat_labels["overdue_books"].configure(text=str(stats["overdue_books"]))
        self.stat_labels["total_fines"].configure(text=f"Tk {stats['total_fines']:.2f}")

        self._update_charts()

    def _update_charts(self) -> None:
        self.ax1.clear()
        self.ax2.clear()
        self._style_axes(self.ax1)
        self._style_axes(self.ax2)

        trends = self.db.analytics_issue_trends(days=30)
        if trends:
            dates = [datetime.strptime(row["issue_date"], "%Y-%m-%d").date() for row in trends]
            counts = [row["count"] for row in trends]
            self.ax1.plot(dates, counts, color=COLORS["primary"], marker="o", linewidth=2)
            self.ax1.fill_between(dates, counts, color=COLORS["primary"], alpha=0.1)
        
        self.ax1.set_title("Book Issues (Last 30 Days)", fontdict={"fontsize": 12, "fontweight": "bold"})
        self.ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        self.ax1.tick_params(axis="x", rotation=45)
        self.ax1.set_ylabel("Issues Count")

        categories = self.db.analytics_popular_categories(limit=5)
        if categories:
            cats = [row["category"] for row in categories]
            cat_counts = [row["count"] for row in categories]
            self.ax2.bar(cats, cat_counts, color=COLORS["accent"], width=0.6)
        
        self.ax2.set_title("Top 5 Categories", fontdict={"fontsize": 12, "fontweight": "bold"})
        self.ax2.set_ylabel("Total Issues")
        self.ax2.tick_params(axis="x", rotation=45)

        self.fig.tight_layout(pad=4.0)
        self.canvas.draw()
