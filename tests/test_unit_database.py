"""
Unit tests for modules/database.py

Covers:
  - Password hashing and verification
  - Code generation logic
  - Book CRUD operations and validations
  - Member CRUD operations and validations
  - Student CRUD operations
  - User management
  - Fine calculation
  - Dashboard statistics
  - Library settings
"""

from __future__ import annotations

import pytest
from datetime import date, timedelta

from modules.database import LibraryDatabase

# ─────────────────────────────────────────────
# Password helpers
# ─────────────────────────────────────────────


class TestPasswordHashing:
    def test_hash_is_deterministic_with_same_salt(self):
        salt = b"\x00" * 16
        h1 = LibraryDatabase.hash_password("secret", salt)
        h2 = LibraryDatabase.hash_password("secret", salt)
        assert h1 == h2

    def test_different_salts_produce_different_hashes(self):
        h1 = LibraryDatabase.hash_password("secret")
        h2 = LibraryDatabase.hash_password("secret")
        # salts are random; hashes should differ (collision probability ≈ 0)
        assert h1 != h2

    def test_verify_correct_password(self):
        hashed = LibraryDatabase.hash_password("mypassword")
        assert LibraryDatabase.verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self):
        hashed = LibraryDatabase.hash_password("mypassword")
        assert LibraryDatabase.verify_password("wrongpassword", hashed) is False

    def test_verify_malformed_hash(self):
        assert LibraryDatabase.verify_password("any", "notahash") is False


# ─────────────────────────────────────────────
# Code generation
# ─────────────────────────────────────────────


class TestCodeGeneration:
    def test_first_book_code(self, db):
        assert db.generate_book_code() == "BK0001"

    def test_sequential_book_codes(self, db):
        db.add_book(
            {
                "title": "Book A",
                "author": "Author A",
                "category": "Cat",
                "publisher": "Pub",
                "isbn": "111",
                "quantity": 1,
                "shelf_location": "A1",
            }
        )
        assert db.generate_book_code() == "BK0002"

    def test_first_member_code(self, db):
        assert db.generate_member_code() == "MB0001"

    def test_first_student_code(self, db):
        assert db.generate_student_code() == "ST0001"

    def test_next_code_with_gaps_uses_max(self):
        codes = ["BK0001", "BK0005", "BK0003"]
        result = LibraryDatabase._next_code("BK", codes)
        assert result == "BK0006"

    def test_next_code_empty_list_starts_at_one(self):
        assert LibraryDatabase._next_code("MB", []) == "MB0001"


# ─────────────────────────────────────────────
# Book CRUD
# ─────────────────────────────────────────────


class TestBookCRUD:
    def test_add_book_returns_id(self, db):
        book_id = db.add_book(
            {
                "title": "Refactoring",
                "author": "Fowler",
                "category": "Programming",
                "publisher": "Addison",
                "isbn": "9780201485677",
                "quantity": 2,
                "shelf_location": "B2",
            }
        )
        assert isinstance(book_id, int)
        assert book_id > 0

    def test_add_book_sets_available_equal_to_quantity(self, db):
        db.add_book(
            {
                "title": "T",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "999",
                "quantity": 5,
                "shelf_location": "X",
            }
        )
        book = db.get_book_by_code("BK0001")
        assert book["available_quantity"] == 5

    def test_duplicate_isbn_raises(self, db):
        db.add_book(
            {
                "title": "A",
                "author": "B",
                "category": "C",
                "publisher": "P",
                "isbn": "SAME",
                "quantity": 1,
                "shelf_location": "Z",
            }
        )
        with pytest.raises(ValueError, match="ISBN"):
            db.add_book(
                {
                    "title": "D",
                    "author": "E",
                    "category": "F",
                    "publisher": "G",
                    "isbn": "SAME",
                    "quantity": 1,
                    "shelf_location": "Z",
                }
            )

    def test_zero_quantity_raises(self, db):
        with pytest.raises(ValueError):
            db.add_book(
                {
                    "title": "T",
                    "author": "A",
                    "category": "C",
                    "publisher": "P",
                    "isbn": "ZQ",
                    "quantity": 0,
                    "shelf_location": "X",
                }
            )

    def test_get_book_by_code(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        assert book is not None
        assert book["title"] == "Clean Code"

    def test_get_book_by_code_not_found(self, db):
        assert db.get_book_by_code("BK9999") is None

    def test_update_book(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        db_with_data.update_book(
            book["id"],
            {
                "title": "Clean Code 2nd Ed",
                "author": "Robert Martin",
                "category": "Programming",
                "publisher": "Prentice Hall",
                "isbn": "9780132350884",
                "quantity": 5,
                "shelf_location": "A2",
            },
        )
        updated = db_with_data.get_book_by_code("BK0001")
        assert updated["title"] == "Clean Code 2nd Ed"
        assert updated["quantity"] == 5

    def test_update_book_quantity_below_issued_raises(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])

        with pytest.raises(ValueError, match="lower than already issued"):
            db_with_data.update_book(
                book["id"],
                {
                    "title": "Clean Code",
                    "author": "Robert Martin",
                    "category": "Programming",
                    "publisher": "Prentice Hall",
                    "isbn": "9780132350884",
                    "quantity": 0,
                    "shelf_location": "A1",
                },
            )

    def test_delete_book(self, db):
        db.add_book(
            {
                "title": "Temp",
                "author": "A",
                "category": "C",
                "publisher": "P",
                "isbn": "TMPB",
                "quantity": 1,
                "shelf_location": "Z",
            }
        )
        book = db.get_book_by_code("BK0001")
        db.delete_book(book["id"])
        assert db.get_book_by_code("BK0001") is None

    def test_delete_issued_book_raises(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])

        with pytest.raises(ValueError, match="currently issued"):
            db_with_data.delete_book(book["id"])

    def test_fetch_books_returns_all(self, db_with_data):
        books = db_with_data.fetch_books()
        assert len(books) == 1
        assert books[0]["title"] == "Clean Code"

    def test_fetch_books_search_by_title(self, db_with_data):
        results = db_with_data.fetch_books(search_text="clean", search_field="title")
        assert len(results) == 1

    def test_fetch_books_search_no_match(self, db_with_data):
        results = db_with_data.fetch_books(
            search_text="Nonexistent", search_field="title"
        )
        assert results == []


# ─────────────────────────────────────────────
# Member CRUD
# ─────────────────────────────────────────────


class TestMemberCRUD:
    def test_add_member(self, db):
        member_id = db.add_member(
            {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "01700000000",
                "address": "1 Test Street",
            }
        )
        assert member_id > 0

    def test_member_code_auto_generated(self, db):
        db.add_member({"name": "M", "email": "", "phone": "", "address": "A"})
        member = db.get_member_by_code("MB0001")
        assert member is not None

    def test_duplicate_email_raises(self, db):
        db.add_member(
            {
                "name": "A",
                "email": "dup@x.com",
                "phone": "111",
                "address": "A",
            }
        )
        with pytest.raises(ValueError):
            db.add_member(
                {
                    "name": "B",
                    "email": "dup@x.com",
                    "phone": "222",
                    "address": "B",
                }
            )

    def test_duplicate_phone_raises(self, db):
        db.add_member(
            {
                "name": "A",
                "email": "a@x.com",
                "phone": "SAMEPHONE",
                "address": "A",
            }
        )
        with pytest.raises(ValueError):
            db.add_member(
                {
                    "name": "B",
                    "email": "b@x.com",
                    "phone": "SAMEPHONE",
                    "address": "B",
                }
            )

    def test_update_member(self, db_with_data):
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.update_member(
            member["id"],
            {
                "member_code": "MB0001",
                "name": "Alice Updated",
                "email": "alice@example.com",
                "phone": "01711000001",
                "address": "999 New Avenue",
            },
        )
        updated = db_with_data.get_member_by_code("MB0001")
        assert updated["name"] == "Alice Updated"

    def test_delete_member_with_active_issue_raises(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])
        with pytest.raises(ValueError, match="active issued books"):
            db_with_data.delete_member(member["id"])

    def test_delete_member_no_issues(self, db_with_data):
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.delete_member(member["id"])
        assert db_with_data.get_member_by_code("MB0001") is None


# ─────────────────────────────────────────────
# Issue / Return + Fine calculation
# ─────────────────────────────────────────────


class TestIssueReturn:
    def test_issue_book_decrements_available(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])
        updated = db_with_data.get_book_by_code("BK0001")
        assert updated["available_quantity"] == book["available_quantity"] - 1

    def test_return_book_increments_available(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        issue_id = db_with_data.issue_book(book["id"], member["id"])
        db_with_data.return_book(issue_id)
        restored = db_with_data.get_book_by_code("BK0001")
        assert restored["available_quantity"] == book["available_quantity"]

    def test_duplicate_issue_same_member_raises(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])
        with pytest.raises(ValueError, match="already issued"):
            db_with_data.issue_book(book["id"], member["id"])

    def test_return_already_returned_raises(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        issue_id = db_with_data.issue_book(book["id"], member["id"])
        db_with_data.return_book(issue_id)
        with pytest.raises(ValueError, match="already been returned"):
            db_with_data.return_book(issue_id)

    def test_no_fine_before_due_date(self):
        today = date.today().isoformat()
        future = (date.today() + timedelta(days=5)).isoformat()
        assert LibraryDatabase.calculate_fine(future, today) == 0.0

    def test_no_fine_on_due_date(self):
        today = date.today().isoformat()
        assert LibraryDatabase.calculate_fine(today, today) == 0.0

    def test_fine_accumulates_at_10_per_day(self):
        due = (date.today() - timedelta(days=5)).isoformat()
        today = date.today().isoformat()
        assert LibraryDatabase.calculate_fine(due, today) == 50.0

    def test_fine_calculation_uses_today_if_no_return_date(self):
        due = (date.today() - timedelta(days=3)).isoformat()
        assert LibraryDatabase.calculate_fine(due) == 30.0


# ─────────────────────────────────────────────
# User management
# ─────────────────────────────────────────────


class TestUserManagement:
    def test_default_admin_seeded(self, db):
        user = db.get_user_by_username("admin")
        assert user is not None
        assert user["role"] == "admin"

    def test_authenticate_valid_user(self, db):
        user = db.authenticate_user("admin", "admin123")
        assert user is not None
        assert user["username"] == "admin"

    def test_authenticate_wrong_password(self, db):
        assert db.authenticate_user("admin", "wrong") is None

    def test_authenticate_unknown_user(self, db):
        assert db.authenticate_user("ghost", "pass") is None

    def test_create_and_fetch_user(self, db):
        db.create_user("staffuser", "staffpass", "staff")
        user = db.get_user_by_username("staffuser")
        assert user["role"] == "staff"

    def test_update_user(self, db):
        db.create_user("orig", "pass", "staff")
        user = db.get_user_by_username("orig")
        db.update_user(user["id"], "renamed", "admin")
        renamed = db.get_user_by_username("renamed")
        assert renamed["role"] == "admin"

    def test_update_user_duplicate_username_raises(self, db):
        db.create_user("user1", "pass1", "staff")
        db.create_user("user2", "pass2", "staff")
        u2 = db.get_user_by_username("user2")
        with pytest.raises(ValueError, match="already exists"):
            db.update_user(u2["id"], "user1", "staff")

    def test_delete_user(self, db):
        db.create_user("todelete", "pass", "staff")
        user = db.get_user_by_username("todelete")
        db.delete_user(user["id"])
        assert db.get_user_by_username("todelete") is None

    def test_change_password(self, db):
        db.create_user("changer", "oldpass", "staff")
        result = db.change_password("changer", "oldpass", "newpass")
        assert result is True
        assert db.authenticate_user("changer", "newpass") is not None
        assert db.authenticate_user("changer", "oldpass") is None

    def test_change_password_wrong_old_password(self, db):
        db.create_user("changer2", "oldpass", "staff")
        result = db.change_password("changer2", "wrongold", "newpass")
        assert result is False


# ─────────────────────────────────────────────
# Dashboard statistics
# ─────────────────────────────────────────────


class TestDashboardStats:
    def test_empty_database_stats(self, db):
        stats = db.dashboard_stats()
        assert stats["total_books"] == 0
        assert stats["total_members"] == 0
        assert stats["books_issued"] == 0
        assert stats["books_available"] == 0
        assert stats["overdue_books"] == 0
        assert stats["total_fines"] == 0.0

    def test_stats_reflect_added_book(self, db_with_data):
        stats = db_with_data.dashboard_stats()
        assert stats["total_books"] == 3  # quantity of Clean Code
        assert stats["books_available"] == 3

    def test_stats_reflect_issued_book(self, db_with_data):
        book = db_with_data.get_book_by_code("BK0001")
        member = db_with_data.get_member_by_code("MB0001")
        db_with_data.issue_book(book["id"], member["id"])
        stats = db_with_data.dashboard_stats()
        assert stats["books_issued"] == 1
        assert stats["books_available"] == 2


# ─────────────────────────────────────────────
# Library settings
# ─────────────────────────────────────────────


class TestLibrarySettings:
    def test_default_library_name(self, db):
        settings = db.get_library_settings()
        assert settings["library_name"] == "Library Management System"

    def test_update_library_settings(self, db):
        db.update_library_settings(
            {
                "library_name": "City Library",
                "phone": "01700000000",
            }
        )
        settings = db.get_library_settings()
        assert settings["library_name"] == "City Library"
        assert settings["phone"] == "01700000000"

    def test_update_settings_preserves_unrelated_keys(self, db):
        db.update_library_settings({"library_name": "X"})
        settings = db.get_library_settings()
        assert "address" in settings
