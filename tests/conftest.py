"""Shared pytest fixtures for the Library Management System test suite."""

from __future__ import annotations

import pytest
from modules.database import LibraryDatabase


@pytest.fixture
def db(tmp_path):
    """Return a fresh in-memory-style database for each test (isolated file per test)."""
    db_file = tmp_path / "test_library.db"
    database = LibraryDatabase(db_path=str(db_file))
    return database


@pytest.fixture
def db_with_data(db):
    """Database pre-loaded with one book, one member, and one student."""
    db.add_book(
        {
            "book_code": "BK0001",
            "title": "Clean Code",
            "author": "Robert Martin",
            "category": "Programming",
            "publisher": "Prentice Hall",
            "isbn": "9780132350884",
            "quantity": 3,
            "shelf_location": "A1",
        }
    )
    db.add_member(
        {
            "name": "Alice Smith",
            "email": "alice@example.com",
            "phone": "01711000001",
            "address": "123 Main Street",
        }
    )
    db.add_student(
        {
            "student_code": "ST0001",
            "full_name": "Bob Jones",
            "class_name": "10",
            "section": "A",
            "roll_no": "001",
            "email": "bob@school.edu",
            "phone": "01811000001",
            "address": "456 School Road",
        }
    )
    return db
