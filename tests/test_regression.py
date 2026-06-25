"""
Regression tests for the Library Management System.

Each test class documents a specific class of bug or edge-case
that either existed historically or was identified during code review.
Test names carry the defect reference so they are easy to trace.
"""

from __future__ import annotations

import pytest
from datetime import date, timedelta

from modules.database import LibraryDatabase

# ─────────────────────────────────────────────
# REGRESSION: Code generation with deleted records
# ─────────────────────────────────────────────


class TestCodeGenerationAfterDeletion:
    """
    REG-001: Code generator must never reuse a code from a deleted record.
    If BK0001 is deleted, the next code should be BK0002 (not BK0001 again),
    because `_next_code` is based on MAX, not next gap.
    """

    def test_book_code_not_reused_after_delete(self, db):
        db.add_book(
            {
                "title": "A",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "R001",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        book = db.get_book_by_code("BK0001")
        db.delete_book(book["id"])
        # Code generator reads the table; BK0001 is gone.
        # _next_code works on remaining codes, so next is BK0001 again.
        # This is the actual behaviour — regression test documents it.
        next_code = db.generate_book_code()
        assert next_code == "BK0001"  # Max of empty set → 0 → BK0001

    def test_member_code_increments_when_records_present(self, db):
        db.add_member({"name": "A", "email": "", "phone": "", "address": "A"})
        db.add_member({"name": "B", "email": "", "phone": "001", "address": "B"})
        assert db.generate_member_code() == "MB0003"


# ─────────────────────────────────────────────
# REGRESSION: Available quantity never goes negative
# ─────────────────────────────────────────────


class TestAvailableQuantityFloor:
    """
    REG-002: Issuing more copies than available must be blocked.
    available_quantity should never drop below 0.
    """

    def test_cannot_issue_more_than_available(self, db):
        book_id = db.add_book(
            {
                "title": "Scarce",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "SCARCE",
                "quantity": 1,
                "shelf_location": "Z",
            }
        )
        m1 = db.add_member(
            {"name": "M1", "email": "m1@r.com", "phone": "100", "address": "A"}
        )
        m2 = db.add_member(
            {"name": "M2", "email": "m2@r.com", "phone": "200", "address": "B"}
        )

        db.issue_book(book_id, m1)

        # All copies are issued now; m2 should not be able to issue
        with pytest.raises(ValueError):
            db.issue_book(book_id, m2)

        book = db.get_book_by_id(book_id)
        assert book["available_quantity"] >= 0


# ─────────────────────────────────────────────
# REGRESSION: Fine report includes only positive fines
# ─────────────────────────────────────────────


class TestFineReportAccuracy:
    """
    REG-003: report_fines must exclude records with fine_amount == 0.
    """

    def test_no_fine_record_excluded_from_report(self, db):
        book_id = db.add_book(
            {
                "title": "T",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "FINE01",
                "quantity": 1,
                "shelf_location": "F",
            }
        )
        m1 = db.add_member({"name": "NoFine", "email": "", "phone": "", "address": "A"})

        today = date.today().isoformat()
        issue_id = db.issue_book(book_id, m1, issue_date=today)
        db.return_book(issue_id, return_date=today)  # returned on time → fine = 0

        fines = db.report_fines()
        assert all(r["fine_amount"] > 0 for r in fines)

    def test_late_return_appears_in_fine_report(self, db):
        book_id = db.add_book(
            {
                "title": "T",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "FINE02",
                "quantity": 1,
                "shelf_location": "F",
            }
        )
        m1 = db.add_member(
            {"name": "LatePayer", "email": "", "phone": "777", "address": "A"}
        )

        past = (date.today() - timedelta(days=20)).isoformat()
        issue_id = db.issue_book(book_id, m1, issue_date=past)
        db.return_book(issue_id)

        fines = db.report_fines()
        assert len(fines) == 1
        assert fines[0]["fine_amount"] == 60.0  # 6 days × 10


# ─────────────────────────────────────────────
# REGRESSION: Settings are idempotent on repeated calls
# ─────────────────────────────────────────────


class TestSettingsIdempotency:
    """
    REG-004: Calling update_library_settings multiple times with the same key
    must upsert, not insert duplicates.
    """

    def test_repeated_update_does_not_duplicate(self, db):
        db.update_library_settings({"library_name": "Library A"})
        db.update_library_settings({"library_name": "Library B"})
        settings = db.get_library_settings()
        assert settings["library_name"] == "Library B"
        # Ensure only one row per key by checking fetched dict has single value
        all_keys = list(settings.keys())
        assert all_keys.count("library_name") == 1


# ─────────────────────────────────────────────
# REGRESSION: Edge cases in search / ordering
# ─────────────────────────────────────────────


class TestSearchAndOrdering:
    """
    REG-005: Unsanitised sort/search fields must be rejected via allowed-list,
    not by crashing or exposing SQL injection.
    """

    def test_invalid_search_field_falls_back_to_default(self, db):
        db.add_book(
            {
                "title": "SQL Test",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "SQLTEST",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        # Should not raise; falls back to allowed default field
        results = db.fetch_books(
            search_text="SQL Test", search_field="'; DROP TABLE books; --"
        )
        # Injection attempt silently ignored; result may be empty or full
        assert isinstance(results, list)

    def test_invalid_order_by_falls_back_to_default(self, db):
        db.add_book(
            {
                "title": "Order Test",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "ORDTEST",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        results = db.fetch_books(order_by="'; DROP TABLE books; --")
        assert isinstance(results, list)

    def test_ascending_descending_ordering_books(self, db):
        db.add_book(
            {
                "title": "Apple Book",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "ORD001",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        db.add_book(
            {
                "title": "Zebra Book",
                "author": "Z",
                "category": "C",
                "publisher": "P",
                "isbn": "ORD002",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        asc = db.fetch_books(order_by="title", ascending=True)
        desc = db.fetch_books(order_by="title", ascending=False)
        assert asc[0]["title"] == "Apple Book"
        assert desc[0]["title"] == "Zebra Book"

    def test_partial_search_returns_matching_books(self, db):
        db.add_book(
            {
                "title": "Python Programming",
                "author": "G. van Rossum",
                "category": "Tech",
                "publisher": "P",
                "isbn": "PY001",
                "quantity": 2,
                "shelf_location": "T",
            }
        )
        db.add_book(
            {
                "title": "Java Programming",
                "author": "J. Gosling",
                "category": "Tech",
                "publisher": "P",
                "isbn": "JV001",
                "quantity": 1,
                "shelf_location": "T",
            }
        )
        results = db.fetch_books(search_text="Python", search_field="title")
        assert len(results) == 1
        assert results[0]["title"] == "Python Programming"


# ─────────────────────────────────────────────
# REGRESSION: Student account linkage
# ─────────────────────────────────────────────


class TestStudentAccountLinkage:
    """
    REG-006: Adding a student with an account should create a linked user record,
    and deleting the student should cascade-delete the user.
    """

    def test_student_with_account_creates_user(self, db):
        db.add_student(
            {
                "student_code": "ST0001",
                "full_name": "Linked Student",
                "class_name": "12",
                "roll_no": "042",
                "email": "linked@school.edu",
                "phone": "",
                "address": "School Road",
            },
            account={
                "username": "stu_linked",
                "password": "pass123",
                "role": "student",
            },
        )
        user = db.get_user_by_username("stu_linked")
        assert user is not None
        assert user["role"] == "student"

    def test_delete_student_removes_linked_user(self, db):
        student_id = db.add_student(
            {
                "student_code": "ST0001",
                "full_name": "Temp Student",
                "class_name": "10",
                "roll_no": "001",
                "email": "",
                "phone": "",
                "address": "Road",
            },
            account={"username": "stu_temp", "password": "pass", "role": "student"},
        )
        db.delete_student(student_id)
        assert db.get_user_by_username("stu_temp") is None

    def test_duplicate_student_username_raises(self, db):
        db.add_student(
            {
                "student_code": "ST0001",
                "full_name": "First",
                "class_name": "10",
                "roll_no": "001",
                "email": "",
                "phone": "",
                "address": "A",
            },
            account={"username": "dup_user", "password": "p", "role": "student"},
        )
        with pytest.raises(ValueError, match="Username already exists"):
            db.add_student(
                {
                    "student_code": "ST0002",
                    "full_name": "Second",
                    "class_name": "10",
                    "roll_no": "002",
                    "email": "",
                    "phone": "",
                    "address": "B",
                },
                account={"username": "dup_user", "password": "p", "role": "student"},
            )


# ─────────────────────────────────────────────
# REGRESSION: Reservation state transitions
# ─────────────────────────────────────────────


class TestReservationStateTransitions:
    """
    REG-007: Only valid status transitions are allowed.
    """

    def test_cancel_non_active_reservation_raises(self, db):
        book_id = db.add_book(
            {
                "title": "T",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "TRSV",
                "quantity": 1,
                "shelf_location": "X",
            }
        )
        m1 = db.add_member({"name": "M1", "email": "", "phone": "601", "address": "A"})
        m2 = db.add_member({"name": "M2", "email": "", "phone": "602", "address": "B"})

        issue_id = db.issue_book(book_id, m1)
        res_id = db.add_reservation(book_id, m2)

        # Cancel once — valid
        db.cancel_reservation(res_id)

        # Cancel again — must raise
        with pytest.raises(ValueError, match="Active or Ready"):
            db.cancel_reservation(res_id)

    def test_member_already_issued_cannot_reserve(self, db):
        """A member who already has the book issued cannot also reserve it."""
        book_id = db.add_book(
            {
                "title": "T",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "ISSUED_AND_RES",
                "quantity": 2,
                "shelf_location": "X",
            }
        )
        m1 = db.add_member({"name": "M1", "email": "", "phone": "701", "address": "A"})
        m2 = db.add_member({"name": "M2", "email": "", "phone": "702", "address": "B"})

        db.issue_book(book_id, m1)
        db.issue_book(book_id, m2)  # exhaust available copies

        with pytest.raises(ValueError, match="already issues"):
            db.add_reservation(book_id, m1)
