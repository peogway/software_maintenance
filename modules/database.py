from __future__ import annotations

import hashlib
import shutil
import sqlite3
import secrets
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


class LibraryDatabase:
    """SQLite data access layer for the Library Management System."""

    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin123"
    DEFAULT_ADMIN_ROLE = "admin"

    def __init__(self, db_path: Optional[str] = None) -> None:
        project_root = Path(__file__).resolve().parent.parent
        self.database_dir = project_root / "database"
        self.backup_dir = project_root / "backup"
        self.database_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path) if db_path else self.database_dir / "library.db"
        self._initialize_database()

    @contextmanager
    def _connection(self) -> Iterable[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            publisher TEXT NOT NULL,
            isbn TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 1,
            available_quantity INTEGER NOT NULL DEFAULT 1,
            shelf_location TEXT NOT NULL,
            added_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            address TEXT NOT NULL,
            join_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            section TEXT,
            roll_no TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            address TEXT NOT NULL,
            user_id INTEGER UNIQUE,
            join_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS issued_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Issued',
            fine_amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        );
        """
        with self._connection() as connection:
            connection.executescript(schema)
        self._migrate_students_table()
        self._seed_default_admin()
        self._seed_default_settings()

    def _table_columns(self, table_name: str) -> set[str]:
        with self._connection() as connection:
            rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}

    def _migrate_students_table(self) -> None:
        if "user_id" in self._table_columns("students"):
            return
        with self._connection() as connection:
            connection.execute("ALTER TABLE students ADD COLUMN user_id INTEGER")

    def _seed_default_admin(self) -> None:
        if self.get_user_by_username(self.DEFAULT_ADMIN_USERNAME):
            return
        self.create_user(
            self.DEFAULT_ADMIN_USERNAME,
            self.DEFAULT_ADMIN_PASSWORD,
            self.DEFAULT_ADMIN_ROLE,
        )

    def _seed_default_settings(self) -> None:
        defaults = {
            "library_name": "Library Management System",
            "address": "",
            "phone": "",
            "email": "",
        }
        with self._connection() as connection:
            for key, value in defaults.items():
                connection.execute(
                    """
                    INSERT OR IGNORE INTO settings (setting_key, setting_value)
                    VALUES (?, ?)
                    """,
                    (key, value),
                )

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> str:
        salt_bytes = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            120_000,
        )
        return "pbkdf2_sha256${}${}${}".format(
            120_000,
            salt_bytes.hex(),
            digest.hex(),
        )

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            )
            return secrets.compare_digest(candidate.hex(), digest_hex)
        except ValueError:
            return False

    def create_user(self, username: str, password: str, role: str = "staff") -> int:
        with self._connection() as connection:
            cursor = self._create_user_record(connection, username, password, role)
            return cursor.lastrowid

    def _create_user_record(
        self,
        connection: sqlite3.Connection,
        username: str,
        password: str,
        role: str = "staff",
    ) -> sqlite3.Cursor:
        username_clean = username.strip()
        if not username_clean:
            raise ValueError("Username is required.")
        if not password:
            raise ValueError("Password is required.")
        password_hash = self.hash_password(password)
        return connection.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username_clean, password_hash, role.strip() or "staff"),
        )

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user["password_hash"]):
            return None
        return user

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        user = self.authenticate_user(username, old_password)
        if not user:
            return False
        new_hash = self.hash_password(new_password)
        with self._connection() as connection:
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user["id"]),
            )
        return True

    def fetch_users(
        self,
        search_text: str = "",
        search_field: str = "username",
        order_by: str = "created_at",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        allowed_fields = {"username", "role", "created_at"}
        allowed_order = {"id", "username", "role", "created_at"}
        field = search_field if search_field in allowed_fields else "username"
        order = order_by if order_by in allowed_order else "created_at"
        direction = "ASC" if ascending else "DESC"
        params: List[Any] = []
        query = "SELECT id, username, role, created_at FROM users"
        if search_text.strip():
            query += f" WHERE {field} LIKE ?"
            params.append(f"%{search_text.strip()}%")
        query += f" ORDER BY {order} {direction}"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def update_user(self, user_id: int, username: str, role: str, password: Optional[str] = None) -> None:
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM users WHERE username = ? AND id != ?",
                (username.strip(), user_id),
            ).fetchone()
            if existing:
                raise ValueError("A user with this username already exists.")

            if password:
                password_hash = self.hash_password(password)
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?, role = ?, password_hash = ?
                    WHERE id = ?
                    """,
                    (username.strip(), role.strip(), password_hash, user_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?, role = ?
                    WHERE id = ?
                    """,
                    (username.strip(), role.strip(), user_id),
                )

    def delete_user(self, user_id: int) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))

    @staticmethod
    def _next_code(prefix: str, existing_codes: List[str], width: int = 4) -> str:
        max_number = 0
        for code in existing_codes:
            try:
                number = int(code.replace(prefix, ""))
            except ValueError:
                continue
            max_number = max(max_number, number)
        return f"{prefix}{max_number + 1:0{width}d}"

    def generate_book_code(self) -> str:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT book_code FROM books ORDER BY id DESC"
            ).fetchall()
        return self._next_code("BK", [row["book_code"] for row in rows])

    def generate_member_code(self) -> str:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT member_code FROM members ORDER BY id DESC"
            ).fetchall()
        return self._next_code("MB", [row["member_code"] for row in rows])

    def generate_student_code(self) -> str:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT student_code FROM students ORDER BY id DESC"
            ).fetchall()
        return self._next_code("ST", [row["student_code"] for row in rows])

    def _book_exists_with_isbn(self, isbn: str, exclude_id: Optional[int] = None) -> bool:
        query = "SELECT 1 FROM books WHERE isbn = ?"
        params: Tuple[Any, ...] = (isbn.strip(),)
        if exclude_id is not None:
            query += " AND id != ?"
            params = (isbn.strip(), exclude_id)
        with self._connection() as connection:
            row = connection.execute(query, params).fetchone()
        return row is not None

    def add_book(self, data: Dict[str, Any]) -> int:
        isbn = data["isbn"].strip()
        if self._book_exists_with_isbn(isbn):
            raise ValueError("A book with this ISBN already exists.")

        book_code = data.get("book_code") or self.generate_book_code()
        quantity = int(data["quantity"])
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO books (
                    book_code, title, author, category, publisher, isbn,
                    quantity, available_quantity, shelf_location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book_code.strip(),
                    data["title"].strip(),
                    data["author"].strip(),
                    data["category"].strip(),
                    data["publisher"].strip(),
                    isbn,
                    quantity,
                    quantity,
                    data["shelf_location"].strip(),
                ),
            )
            return cursor.lastrowid

    def update_book(self, book_id: int, data: Dict[str, Any]) -> None:
        if self._book_exists_with_isbn(data["isbn"], exclude_id=book_id):
            raise ValueError("A book with this ISBN already exists.")

        with self._connection() as connection:
            current = connection.execute(
                "SELECT quantity, available_quantity FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if not current:
                raise ValueError("Book not found.")

            current_quantity = int(current["quantity"])
            current_available = int(current["available_quantity"])
            issued_count = current_quantity - current_available
            new_quantity = int(data["quantity"])
            if new_quantity < issued_count:
                raise ValueError("Quantity cannot be lower than already issued copies.")

            new_available = new_quantity - issued_count
            connection.execute(
                """
                UPDATE books
                SET title = ?, author = ?, category = ?, publisher = ?, isbn = ?,
                    quantity = ?, available_quantity = ?, shelf_location = ?
                WHERE id = ?
                """,
                (
                    data["title"].strip(),
                    data["author"].strip(),
                    data["category"].strip(),
                    data["publisher"].strip(),
                    data["isbn"].strip(),
                    new_quantity,
                    new_available,
                    data["shelf_location"].strip(),
                    book_id,
                ),
            )

    def delete_book(self, book_id: int) -> None:
        with self._connection() as connection:
            active_issue = connection.execute(
                """
                SELECT 1 FROM issued_books
                WHERE book_id = ? AND status = 'Issued'
                LIMIT 1
                """,
                (book_id,),
            ).fetchone()
            if active_issue:
                raise ValueError("Cannot delete a book that is currently issued.")
            connection.execute("DELETE FROM books WHERE id = ?", (book_id,))

    def fetch_books(
        self,
        search_text: str = "",
        search_field: str = "title",
        order_by: str = "title",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        allowed_fields = {"title", "author", "isbn", "category"}
        allowed_order = {
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
        }
        field = search_field if search_field in allowed_fields else "title"
        order = order_by if order_by in allowed_order else "title"
        direction = "ASC" if ascending else "DESC"
        params: List[Any] = []
        query = "SELECT * FROM books"
        if search_text.strip():
            query += f" WHERE {field} LIKE ?"
            params.append(f"%{search_text.strip()}%")
        query += f" ORDER BY {order} {direction}"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_book_by_code(self, book_code: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM books WHERE book_code = ?",
                (book_code.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def _member_exists(self, member_code: str, email: Optional[str], phone: Optional[str], exclude_id: Optional[int] = None) -> bool:
        clauses = ["member_code = ?"]
        params: List[Any] = [member_code.strip()]
        if email:
            clauses.append("email = ?")
            params.append(email.strip())
        if phone:
            clauses.append("phone = ?")
            params.append(phone.strip())

        query = "SELECT 1 FROM members WHERE (" + " OR ".join(clauses) + ")"
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)

        with self._connection() as connection:
            row = connection.execute(query, params).fetchone()
        return row is not None

    def add_member(self, data: Dict[str, Any]) -> int:
        member_code = data.get("member_code") or self.generate_member_code()
        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None
        if self._member_exists(member_code, email, phone):
            raise ValueError("A member with the same code, email, or phone already exists.")

        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO members (member_code, name, email, phone, address)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    member_code.strip(),
                    data["name"].strip(),
                    email,
                    phone,
                    data["address"].strip(),
                ),
            )
            return cursor.lastrowid

    def update_member(self, member_id: int, data: Dict[str, Any]) -> None:
        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None
        if self._member_exists(data["member_code"], email, phone, exclude_id=member_id):
            raise ValueError("A member with the same code, email, or phone already exists.")

        with self._connection() as connection:
            connection.execute(
                """
                UPDATE members
                SET member_code = ?, name = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (
                    data["member_code"].strip(),
                    data["name"].strip(),
                    email,
                    phone,
                    data["address"].strip(),
                    member_id,
                ),
            )

    def delete_member(self, member_id: int) -> None:
        with self._connection() as connection:
            active_issue = connection.execute(
                """
                SELECT 1 FROM issued_books
                WHERE member_id = ? AND status = 'Issued'
                LIMIT 1
                """,
                (member_id,),
            ).fetchone()
            if active_issue:
                raise ValueError("Cannot delete a member with active issued books.")
            connection.execute("DELETE FROM members WHERE id = ?", (member_id,))

    def fetch_members(
        self,
        search_text: str = "",
        search_field: str = "name",
        order_by: str = "name",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        allowed_fields = {"name", "member_code", "phone"}
        allowed_order = {"member_code", "name", "email", "phone", "address", "join_date"}
        field = search_field if search_field in allowed_fields else "name"
        order = order_by if order_by in allowed_order else "name"
        direction = "ASC" if ascending else "DESC"
        params: List[Any] = []
        query = "SELECT * FROM members"
        if search_text.strip():
            query += f" WHERE {field} LIKE ?"
            params.append(f"%{search_text.strip()}%")
        query += f" ORDER BY {order} {direction}"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_member_by_id(self, member_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM members WHERE id = ?",
                (member_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_member_by_code(self, member_code: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM members WHERE member_code = ?",
                (member_code.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def _student_exists(
        self,
        student_code: str,
        roll_no: str,
        email: Optional[str],
        phone: Optional[str],
        exclude_id: Optional[int] = None,
    ) -> bool:
        clauses = ["student_code = ?", "roll_no = ?"]
        params: List[Any] = [student_code.strip(), roll_no.strip()]
        if email:
            clauses.append("email = ?")
            params.append(email.strip())
        if phone:
            clauses.append("phone = ?")
            params.append(phone.strip())

        query = "SELECT 1 FROM students WHERE (" + " OR ".join(clauses) + ")"
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)

        with self._connection() as connection:
            row = connection.execute(query, params).fetchone()
        return row is not None

    def add_student(self, data: Dict[str, Any], account: Optional[Dict[str, Any]] = None) -> int:
        student_code = data.get("student_code") or self.generate_student_code()
        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None

        with self._connection() as connection:
            user_id = None
            if account:
                username = account.get("username", "").strip()
                password = account.get("password", "")
                role = account.get("role", "student").strip() or "student"
                existing_user = connection.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
                if existing_user:
                    raise ValueError("A user with this username already exists.")
                user_id = self._create_user_record(connection, username, password, role).lastrowid

            if self._student_exists(student_code, data["roll_no"], email, phone):
                raise ValueError("A student with the same code, roll number, email, or phone already exists.")

            cursor = connection.execute(
                """
                INSERT INTO students (
                    student_code, full_name, class_name, section, roll_no, email, phone, address, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_code.strip(),
                    data["full_name"].strip(),
                    data["class_name"].strip(),
                    data.get("section", "").strip() or None,
                    data["roll_no"].strip(),
                    email,
                    phone,
                    data["address"].strip(),
                    user_id,
                ),
            )
            return cursor.lastrowid

    def update_student(self, student_id: int, data: Dict[str, Any], account: Optional[Dict[str, Any]] = None) -> None:
        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None

        with self._connection() as connection:
            current = connection.execute(
                "SELECT id, user_id FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()
            if not current:
                raise ValueError("Student not found.")

            user_id = current["user_id"]
            if account:
                username = account.get("username", "").strip()
                password = account.get("password", "")
                role = account.get("role", "student").strip() or "student"
                if user_id:
                    duplicate_user = connection.execute(
                        "SELECT 1 FROM users WHERE username = ? AND id != ?",
                        (username, user_id),
                    ).fetchone()
                    if duplicate_user:
                        raise ValueError("A user with this username already exists.")
                    if password:
                        connection.execute(
                            """
                            UPDATE users
                            SET username = ?, role = ?, password_hash = ?
                            WHERE id = ?
                            """,
                            (username, role, self.hash_password(password), user_id),
                        )
                    else:
                        connection.execute(
                            """
                            UPDATE users
                            SET username = ?, role = ?
                            WHERE id = ?
                            """,
                            (username, role, user_id),
                        )
                else:
                    existing_user = connection.execute(
                        "SELECT 1 FROM users WHERE username = ?",
                        (username,),
                    ).fetchone()
                    if existing_user:
                        raise ValueError("A user with this username already exists.")
                    user_id = self._create_user_record(connection, username, password, role).lastrowid

            if self._student_exists(data["student_code"], data["roll_no"], email, phone, exclude_id=student_id):
                raise ValueError("A student with the same code, roll number, email, or phone already exists.")

            connection.execute(
                """
                UPDATE students
                SET student_code = ?, full_name = ?, class_name = ?, section = ?, roll_no = ?,
                    email = ?, phone = ?, address = ?, user_id = ?
                WHERE id = ?
                """,
                (
                    data["student_code"].strip(),
                    data["full_name"].strip(),
                    data["class_name"].strip(),
                    data.get("section", "").strip() or None,
                    data["roll_no"].strip(),
                    email,
                    phone,
                    data["address"].strip(),
                    user_id,
                    student_id,
                ),
            )

    def delete_student(self, student_id: int) -> None:
        with self._connection() as connection:
            student = connection.execute(
                "SELECT user_id FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()
            if student and student["user_id"]:
                connection.execute("DELETE FROM users WHERE id = ?", (student["user_id"],))
            connection.execute("DELETE FROM students WHERE id = ?", (student_id,))

    def fetch_students(
        self,
        search_text: str = "",
        search_field: str = "full_name",
        order_by: str = "full_name",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        allowed_fields = {"full_name", "student_code", "roll_no", "class_name"}
        allowed_order = {"student_code", "full_name", "class_name", "section", "roll_no", "email", "phone", "address", "join_date"}
        field = search_field if search_field in allowed_fields else "full_name"
        order = order_by if order_by in allowed_order else "full_name"
        direction = "ASC" if ascending else "DESC"
        params: List[Any] = []
        query = """
            SELECT
                students.*,
                users.username AS account_username,
                users.role AS account_role
            FROM students
            LEFT JOIN users ON users.id = students.user_id
        """
        if search_text.strip():
            query += f" WHERE students.{field} LIKE ?"
            params.append(f"%{search_text.strip()}%")
        query += f" ORDER BY {order} {direction}"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT students.*, users.username AS account_username, users.role AS account_role
                FROM students
                LEFT JOIN users ON users.id = students.user_id
                WHERE students.id = ?
                """,
                (student_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_student_by_code(self, student_code: str) -> Optional[Dict[str, Any]]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT students.*, users.username AS account_username, users.role AS account_role
                FROM students
                LEFT JOIN users ON users.id = students.user_id
                WHERE students.student_code = ?
                """,
                (student_code.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def issue_book(self, book_id: int, member_id: int, issue_date: Optional[str] = None) -> int:
        issue_day = date.fromisoformat(issue_date) if issue_date else date.today()
        due_day = issue_day + timedelta(days=14)

        with self._connection() as connection:
            book = connection.execute(
                "SELECT available_quantity FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if not book:
                raise ValueError("Book not found.")
            if int(book["available_quantity"]) <= 0:
                raise ValueError("No available copies left for this book.")

            member = connection.execute(
                "SELECT id FROM members WHERE id = ?",
                (member_id,),
            ).fetchone()
            if not member:
                raise ValueError("Member not found.")

            existing_issue = connection.execute(
                """
                SELECT 1 FROM issued_books
                WHERE book_id = ? AND member_id = ? AND status = 'Issued'
                LIMIT 1
                """,
                (book_id, member_id),
            ).fetchone()
            if existing_issue:
                raise ValueError("This book is already issued to the selected member.")

            cursor = connection.execute(
                """
                INSERT INTO issued_books (book_id, member_id, issue_date, due_date, status)
                VALUES (?, ?, ?, ?, 'Issued')
                """,
                (
                    book_id,
                    member_id,
                    issue_day.isoformat(),
                    due_day.isoformat(),
                ),
            )
            connection.execute(
                """
                UPDATE books
                SET available_quantity = available_quantity - 1
                WHERE id = ?
                """,
                (book_id,),
            )
            return cursor.lastrowid

    @staticmethod
    def calculate_fine(due_date: str, return_date: Optional[str] = None) -> float:
        due_day = date.fromisoformat(due_date)
        end_day = date.fromisoformat(return_date) if return_date else date.today()
        overdue_days = (end_day - due_day).days
        if overdue_days <= 0:
            return 0.0
        return float(overdue_days * 10)

    def return_book(self, issue_id: int, return_date: Optional[str] = None) -> float:
        return_day = date.fromisoformat(return_date) if return_date else date.today()
        with self._connection() as connection:
            issue = connection.execute(
                """
                SELECT * FROM issued_books
                WHERE id = ?
                """,
                (issue_id,),
            ).fetchone()
            if not issue:
                raise ValueError("Issue record not found.")
            if issue["status"] == "Returned":
                raise ValueError("This book has already been returned.")

            fine = self.calculate_fine(issue["due_date"], return_day.isoformat())
            connection.execute(
                """
                UPDATE issued_books
                SET return_date = ?, status = 'Returned', fine_amount = ?
                WHERE id = ?
                """,
                (return_day.isoformat(), fine, issue_id),
            )
            connection.execute(
                """
                UPDATE books
                SET available_quantity = available_quantity + 1
                WHERE id = ?
                """,
                (issue["book_id"],),
            )
        return fine

    def fetch_issued_books(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT
                issued_books.id,
                issued_books.book_id,
                issued_books.member_id,
                issued_books.issue_date,
                issued_books.due_date,
                issued_books.return_date,
                issued_books.status,
                issued_books.fine_amount,
                books.book_code,
                books.title,
                books.author,
                members.member_code,
                members.name AS member_name,
                members.phone
            FROM issued_books
            JOIN books ON books.id = issued_books.book_id
            JOIN members ON members.id = issued_books.member_id
        """
        params: List[Any] = []
        if status:
            query += " WHERE issued_books.status = ?"
            params.append(status)
        query += " ORDER BY issued_books.id DESC"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def dashboard_stats(self) -> Dict[str, Any]:
        today = date.today().isoformat()
        with self._connection() as connection:
            total_books = connection.execute("SELECT COALESCE(SUM(quantity), 0) AS total FROM books").fetchone()["total"]
            total_members = connection.execute("SELECT COUNT(*) AS total FROM members").fetchone()["total"]
            total_students = connection.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"]
            books_issued = connection.execute(
                "SELECT COUNT(*) AS total FROM issued_books WHERE status = 'Issued'"
            ).fetchone()["total"]
            books_available = connection.execute(
                "SELECT COALESCE(SUM(available_quantity), 0) AS total FROM books"
            ).fetchone()["total"]
            overdue_books = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM issued_books
                WHERE status = 'Issued' AND due_date < ?
                """,
                (today,),
            ).fetchone()["total"]
            total_fines = connection.execute(
                "SELECT COALESCE(SUM(fine_amount), 0) AS total FROM issued_books"
            ).fetchone()["total"]
        return {
            "total_books": int(total_books),
            "total_members": int(total_members),
            "total_students": int(total_students),
            "books_issued": int(books_issued),
            "books_available": int(books_available),
            "overdue_books": int(overdue_books),
            "total_fines": float(total_fines),
        }

    def report_available_books(self) -> List[Dict[str, Any]]:
        return [book for book in self.fetch_books(order_by="title") if int(book["available_quantity"]) > 0]

    def report_issued_books(self) -> List[Dict[str, Any]]:
        return self.fetch_issued_books(status="Issued")

    def report_overdue_books(self) -> List[Dict[str, Any]]:
        today = date.today().isoformat()
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    issued_books.id,
                    books.book_code,
                    books.title,
                    members.member_code,
                    members.name AS member_name,
                    issued_books.issue_date,
                    issued_books.due_date,
                    issued_books.status,
                    issued_books.fine_amount
                FROM issued_books
                JOIN books ON books.id = issued_books.book_id
                JOIN members ON members.id = issued_books.member_id
                WHERE issued_books.status = 'Issued' AND issued_books.due_date < ?
                ORDER BY issued_books.due_date ASC
                """,
                (today,),
            ).fetchall()
        return [dict(row) for row in rows]

    def report_members(self) -> List[Dict[str, Any]]:
        return self.fetch_members(order_by="name")

    def report_students(self) -> List[Dict[str, Any]]:
        return self.fetch_students(order_by="full_name")

    def report_fines(self) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    issued_books.id,
                    books.book_code,
                    books.title,
                    members.member_code,
                    members.name AS member_name,
                    issued_books.issue_date,
                    issued_books.due_date,
                    issued_books.return_date,
                    issued_books.status,
                    issued_books.fine_amount
                FROM issued_books
                JOIN books ON books.id = issued_books.book_id
                JOIN members ON members.id = issued_books.member_id
                WHERE issued_books.fine_amount > 0
                ORDER BY issued_books.id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_library_settings(self) -> Dict[str, str]:
        with self._connection() as connection:
            rows = connection.execute("SELECT setting_key, setting_value FROM settings").fetchall()
        return {row["setting_key"]: row["setting_value"] for row in rows}

    def update_library_settings(self, settings: Dict[str, str]) -> None:
        with self._connection() as connection:
            for key, value in settings.items():
                connection.execute(
                    """
                    INSERT INTO settings (setting_key, setting_value)
                    VALUES (?, ?)
                    ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
                    """,
                    (key, value),
                )

    def backup_database(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"library_{timestamp}.db"
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore_database(self, backup_file: str) -> None:
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError("Backup file not found.")
        shutil.copy2(backup_path, self.db_path)
        self._initialize_database()

    def analytics_issue_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT issue_date, COUNT(*) AS count
                FROM issued_books
                WHERE issue_date >= ?
                GROUP BY issue_date
                ORDER BY issue_date ASC
                """,
                (start_date.isoformat(),),
            ).fetchall()
        return [dict(row) for row in rows]

    def analytics_popular_categories(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT books.category, COUNT(issued_books.id) AS count
                FROM books
                LEFT JOIN issued_books ON books.id = issued_books.book_id
                GROUP BY books.category
                ORDER BY count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search_all_books(self, text: str) -> List[Dict[str, Any]]:
        return self.fetch_books(text, "title")

    def search_all_members(self, text: str) -> List[Dict[str, Any]]:
        return self.fetch_members(text, "name")
