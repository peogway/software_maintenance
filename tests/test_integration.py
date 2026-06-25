"""
Integration tests for the Library Management System.

Scenario 1 — Full book lifecycle:
  Add book → issue to member → check overdue → return with fine → confirm stats.

Scenario 2 — Reservation queue lifecycle:
  Books fully issued → member reserves → queue managed → book returned → reservation
  becomes Ready → issue to reserved member → reservation Fulfilled.
"""

from __future__ import annotations

import pytest
from datetime import date, timedelta

from modules.database import LibraryDatabase

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _add_book(db, *, isbn="ISBN001", quantity=1):
    return db.add_book(
        {
            "title": "Integration Book",
            "author": "Test Author",
            "category": "Testing",
            "publisher": "Test Pub",
            "isbn": isbn,
            "quantity": quantity,
            "shelf_location": "T1",
        }
    )


def _add_member(db, *, name="Member One", email="", phone=""):
    return db.add_member(
        {
            "name": name,
            "email": email,
            "phone": phone,
            "address": "Test Address",
        }
    )


# ─────────────────────────────────────────────
# Scenario 1 – Full book lifecycle
# ─────────────────────────────────────────────


class TestFullBookLifecycle:
    """Issue, track overdue, return with fine, verify statistics throughout."""

    def test_issue_then_return_no_fine(self, db):
        """Book returned on the issue date — no fine expected."""
        book_id = _add_book(db)
        member_id = _add_member(db)
        today = date.today().isoformat()

        issue_id = db.issue_book(book_id, member_id, issue_date=today)
        fine = db.return_book(issue_id, return_date=today)

        assert fine == 0.0
        book = db.get_book_by_id(book_id)
        assert book["available_quantity"] == 1

    def test_issue_overdue_return_accrues_fine(self, db):
        """Book returned 7 days past due date (21 days after issue) → fine = 70 Tk."""
        book_id = _add_book(db)
        member_id = _add_member(db)

        issue_date = (date.today() - timedelta(days=21)).isoformat()
        return_date = date.today().isoformat()

        issue_id = db.issue_book(book_id, member_id, issue_date=issue_date)
        fine = db.return_book(issue_id, return_date=return_date)

        # 21 days issued, 14-day grace → 7 overdue days × 10 = 70
        assert fine == 70.0

    def test_stats_updated_across_lifecycle(self, db):
        """Dashboard stats correctly reflect each phase of the lifecycle."""
        book_id = _add_book(db, quantity=2)
        m1 = _add_member(db, name="M1", email="m1@x.com", phone="001")
        m2 = _add_member(db, name="M2", email="m2@x.com", phone="002")

        # Phase 1: both books issued
        today = date.today().isoformat()
        id1 = db.issue_book(book_id, m1, issue_date=today)
        id2 = db.issue_book(book_id, m2, issue_date=today)

        stats = db.dashboard_stats()
        assert stats["books_issued"] == 2
        assert stats["books_available"] == 0

        # Phase 2: one returned
        db.return_book(id1)
        stats = db.dashboard_stats()
        assert stats["books_issued"] == 1
        assert stats["books_available"] == 1

        # Phase 3: both returned, fines accumulate
        past = (date.today() - timedelta(days=20)).isoformat()
        issue_id_late = db.issue_book(book_id, m1, issue_date=past)
        db.return_book(issue_id_late)
        stats = db.dashboard_stats()
        assert stats["total_fines"] == 60.0  # 6 overdue days × 10

    def test_report_overdue_books(self, db):
        """Overdue report lists only currently-issued books past due date."""
        book_id = _add_book(db)
        m1 = _add_member(db, name="Late Member", phone="999")
        past_issue = (date.today() - timedelta(days=20)).isoformat()
        db.issue_book(book_id, m1, issue_date=past_issue)

        overdue = db.report_overdue_books()
        assert len(overdue) == 1
        assert overdue[0]["member_name"] == "Late Member"

    def test_returned_books_excluded_from_overdue(self, db):
        """Returned books do not appear in the overdue report."""
        book_id = _add_book(db)
        m1 = _add_member(db, name="On Time", phone="888")

        past_issue = (date.today() - timedelta(days=20)).isoformat()
        issue_id = db.issue_book(book_id, m1, issue_date=past_issue)
        db.return_book(issue_id)

        overdue = db.report_overdue_books()
        assert overdue == []

    def test_full_crud_and_search_pipeline(self, db):
        """Add → search → update → search again → delete → confirm gone."""
        _add_book(db, isbn="SEARCH001")
        books = db.fetch_books(search_text="Integration", search_field="title")
        assert len(books) == 1

        book = books[0]
        db.update_book(
            book["id"],
            {
                "title": "Updated Integration Book",
                "author": "New Author",
                "category": "Testing",
                "publisher": "Test Pub",
                "isbn": "SEARCH001",
                "quantity": 1,
                "shelf_location": "T2",
            },
        )
        results = db.fetch_books(search_text="Updated", search_field="title")
        assert len(results) == 1
        assert results[0]["shelf_location"] == "T2"

        db.delete_book(book["id"])
        assert db.fetch_books(search_text="Updated", search_field="title") == []


# ─────────────────────────────────────────────
# Scenario 2 – Reservation queue lifecycle
# ─────────────────────────────────────────────


class TestReservationQueueLifecycle:
    """
    Full reservation workflow:
    book is fully issued → members queue up → book returned →
    first in queue goes Ready → issued → Fulfilled.
    """

    def _setup(self, db):
        """One book with qty=1, two members. Book issued to m1."""
        book_id = _add_book(db, isbn="RESV001", quantity=1)
        m1 = _add_member(db, name="Holder", email="h@x.com", phone="111")
        m2 = _add_member(db, name="Waiter", email="w@x.com", phone="222")
        issue_id = db.issue_book(book_id, m1)
        return book_id, m1, m2, issue_id

    def test_cannot_reserve_available_book(self, db):
        """Reservation is blocked when a copy is still available."""
        book_id = _add_book(db, isbn="AVAIL")
        m1 = _add_member(db, name="Eager", phone="300")
        with pytest.raises(ValueError, match="available"):
            db.add_reservation(book_id, m1)

    def test_reservation_created_when_fully_issued(self, db):
        book_id, m1, m2, _ = self._setup(db)
        res_id = db.add_reservation(book_id, m2)
        assert res_id > 0

        res = db.get_reservation_by_id(res_id)
        assert res["status"] == "Active"
        assert res["queue_pos"] == 1

    def test_reserved_quantity_increments(self, db):
        book_id, m1, m2, _ = self._setup(db)
        db.add_reservation(book_id, m2)

        book = db.get_book_by_id(book_id)
        assert book["reserved_quantity"] == 1

    def test_return_triggers_ready_for_first_in_queue(self, db):
        book_id, m1, m2, issue_id = self._setup(db)
        db.add_reservation(book_id, m2)

        db.return_book(issue_id)

        reservations = db.get_reservations_by_book_id(book_id)
        ready = [r for r in reservations if r["status"] == "Ready"]
        assert len(ready) == 1
        assert ready[0]["member_name"] == "Waiter"

    def test_issue_to_reserved_member_fulfills_reservation(self, db):
        book_id, m1, m2, issue_id = self._setup(db)
        db.add_reservation(book_id, m2)
        db.return_book(issue_id)

        # Issue book to the member who is Ready
        db.issue_book(book_id, m2)

        reservations = db.get_reservations_by_book_id(book_id)
        fulfilled = [r for r in reservations if r["status"] == "Fulfilled"]
        assert len(fulfilled) == 1

    def test_cancel_reservation_adjusts_reserved_quantity(self, db):
        book_id, m1, m2, _ = self._setup(db)
        res_id = db.add_reservation(book_id, m2)

        book_before = db.get_book_by_id(book_id)
        db.cancel_reservation(res_id)
        book_after = db.get_book_by_id(book_id)

        assert book_after["reserved_quantity"] == book_before["reserved_quantity"] - 1

    def test_queue_position_management(self, db):
        """Three members queue; cancelling position 1 shifts others down."""
        book_id = _add_book(db, isbn="QUEUE01", quantity=1)
        m1 = _add_member(db, name="Holder", email="h@q.com", phone="401")
        m2 = _add_member(db, name="W1", email="w1@q.com", phone="402")
        m3 = _add_member(db, name="W2", email="w2@q.com", phone="403")
        m4 = _add_member(db, name="W3", email="w3@q.com", phone="404")

        issue_id = db.issue_book(book_id, m1)
        res2 = db.add_reservation(book_id, m2)
        res3 = db.add_reservation(book_id, m3)
        db.add_reservation(book_id, m4)

        # Cancel the first in queue
        db.cancel_reservation(res2)

        # W2 should now be position 1, W3 position 2
        r3 = db.get_reservation_by_id(res3)
        assert r3["queue_pos"] == 1

    def test_expire_ready_reservation(self, db):
        """An expired Ready reservation removes reserved quantity and updates status."""
        book_id, m1, m2, issue_id = self._setup(db)
        res_id = db.add_reservation(book_id, m2)

        # Simulate return → m2 goes Ready
        db.return_book(issue_id)

        # Manually expire by back-dating expiry in DB
        from modules.database import LibraryDatabase as _DB

        yesterday = (
            __import__("datetime").date.today()
            - __import__("datetime").timedelta(days=1)
        ).isoformat()
        with db._connection() as conn:
            conn.execute(
                "UPDATE reservations SET expiry_date=? WHERE id=?",
                (yesterday, res_id),
            )

        count = db.expire_reservations()
        assert count == 1

        res = db.get_reservation_by_id(res_id)
        assert res["status"] == "Expired"

    def test_duplicate_reservation_same_member_raises(self, db):
        book_id, m1, m2, _ = self._setup(db)
        db.add_reservation(book_id, m2)
        with pytest.raises(ValueError, match="Active reservation"):
            db.add_reservation(book_id, m2)
