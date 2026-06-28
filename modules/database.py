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
            reserved_quantity INTEGER NOT NULL DEFAULT 0,
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

        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            reserved_date TEXT NOT NULL,
            ready_date TEXT DEFAULT NULL,
            expiry_date TEXT DEFAULT NULL,
            fulfill_date TEXT DEFAULT NULL,
            queue_pos INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
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

    def _exists_any(
        self,
        table: str,
        conditions: Dict[str, Any],
        exclude_id: Optional[int] = None,
        id_field: str = "id",
    ) -> bool:
        clauses = []
        params = []

        for k, v in conditions.items():
            if v is not None and v != "":
                clauses.append(f"{k} = ?")
                params.append(str(v).strip())

        if not clauses:
            raise ValueError("No conditions provided.")

        ALLOWED_TABLES = {"members", "students", "books"}
        if table not in ALLOWED_TABLES:
            raise ValueError("Invalid query")

        query = f"SELECT 1 FROM {table} WHERE (" + " OR ".join(clauses) + ")"

        if exclude_id is not None:
            query += f" AND {id_field} != ?"
            params.append(exclude_id)

        with self._connection() as connection:
            return connection.execute(query, params).fetchone() is not None

    def _get_by_field(
        self,
        table: str,
        field: str,
        value: Any,
    ):

        allowed = {
            "users": {"id", "username"},
            "books": {"id", "book_code"},
            "members": {"id", "member_code"},
        }

        if table not in allowed or field not in allowed[table]:
            raise ValueError("Invalid query")

        with self._connection() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {field} = ?",
                (value,),
            ).fetchone()

        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._get_by_field("users", "id", user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self._get_by_field("users", "username", username)

    def authenticate_user(
        self, username: str, password: str
    ) -> Optional[Dict[str, Any]]:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user["password_hash"]):
            return None
        return user

    def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> bool:
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

    def _fetch_records(
        self,
        table: str,
        search_text: str,
        search_field: str,
        order_by: str,
        ascending: bool,
        allowed_fields: set[str],
        allowed_order: set[str],
    ) -> List[Dict[str, Any]]:
        field = (
            search_field
            if search_field in allowed_fields
            else sorted(allowed_fields)[0]
        )
        order = order_by if order_by in allowed_order else sorted(allowed_order)[0]
        direction = "ASC" if ascending else "DESC"

        params: List[Any] = []
        query = f"SELECT * FROM {table}"

        if search_text.strip():
            query += f" WHERE {field} LIKE ?"
            params.append(f"%{search_text.strip()}%")

        query += f" ORDER BY {order} {direction}"

        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def fetch_users(
        self,
        search_text: str = "",
        search_field: str = "username",
        order_by: str = "created_at",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        return self._fetch_records(
            table="users",
            search_text=search_text,
            search_field=search_field,
            order_by=order_by,
            ascending=ascending,
            allowed_fields={"username", "role", "created_at"},
            allowed_order={"id", "username", "role", "created_at"},
        )

    def update_user(
        self, user_id: int, username: str, role: str, password: Optional[str] = None
    ) -> None:
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

    def _generate_code(self, table: str, column: str, prefix: str) -> str:
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT {column} FROM {table} ORDER BY id DESC"
            ).fetchall()

        return self._next_code(prefix, [row[column] for row in rows])

    def generate_book_code(self) -> str:
        return self._generate_code("books", "book_code", "BK")

    def generate_member_code(self) -> str:
        return self._generate_code("members", "member_code", "MB")

    def generate_student_code(self) -> str:
        return self._generate_code("students", "student_code", "ST")

    def add_book(self, data: Dict[str, Any]) -> int:
        isbn = data["isbn"].strip()
        if self._exists_any("books", {"isbn": isbn}):
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
        if self._exists_any(
            "books", {"isbn": data["isbn"].strip()}, exclude_id=book_id
        ):
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
        return self._fetch_records(
            table="books",
            search_text=search_text,
            search_field=search_field,
            order_by=order_by,
            ascending=ascending,
            allowed_fields={"title", "author", "isbn", "category"},
            allowed_order={
                "book_code",
                "title",
                "author",
                "category",
                "publisher",
                "isbn",
                "quantity",
                "available_quantity",
                "reserved_quantity",
                "shelf_location",
                "added_date",
            },
        )

    def get_book_by_id(self, book_id: int) -> Optional[Dict[str, Any]]:
        return self._get_by_field("books", "id", book_id)

    def get_book_by_code(self, book_code: str) -> Optional[Dict[str, Any]]:
        return self._get_by_field("books", "book_code", book_code)

    def save_member(
        self,
        data: Dict[str, Any],
        member_id: Optional[int] = None,
    ) -> Optional[int]:
        member_code = data.get("member_code") or self.generate_member_code()
        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None

        if self._exists_any(
            "members",
            {"member_code": member_code, "email": email, "phone": phone},
            exclude_id=member_id,
        ):
            raise ValueError(
                "A member with the same code, email, or phone already exists."
            )

        with self._connection() as connection:
            if member_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO members (
                        member_code, name, email, phone, address
                    )
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

            connection.execute(
                """
                UPDATE members
                SET member_code = ?, name = ?, email = ?, phone = ?, address = ?
                WHERE id = ?
                """,
                (
                    member_code.strip(),
                    data["name"].strip(),
                    email,
                    phone,
                    data["address"].strip(),
                    member_id,
                ),
            )

        return None

    def add_member(self, data: Dict[str, Any]) -> int:
        return self.save_member(data)

    def update_member(self, member_id: int, data: Dict[str, Any]) -> None:
        self.save_member(data, member_id)

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
        return self._fetch_records(
            table="members",
            search_text=search_text,
            search_field=search_field,
            order_by=order_by,
            ascending=ascending,
            allowed_fields={"name", "member_code", "phone"},
            allowed_order={
                "member_code",
                "name",
                "email",
                "phone",
                "address",
                "join_date",
            },
        )

    def get_member_by_id(self, member_id: int) -> Optional[Dict[str, Any]]:
        return self._get_by_field("members", "id", member_id)

    def get_member_by_code(self, member_code: str) -> Optional[Dict[str, Any]]:
        return self._get_by_field("members", "member_code", member_code)

    def save_student(
        self,
        data: Dict[str, Any],
        student_id: Optional[int] = None,
        account: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:

        email = data.get("email", "").strip() or None
        phone = data.get("phone", "").strip() or None

        with self._connection() as connection:

            current_user_id = None

            if student_id:
                current = connection.execute(
                    "SELECT id, user_id FROM students WHERE id = ?",
                    (student_id,),
                ).fetchone()

                if not current:
                    raise ValueError("Student not found.")

                current_user_id = current["user_id"]

            user_id = current_user_id

            if account:
                username = account.get("username", "").strip()
                password = account.get("password", "")
                role = account.get("role", "student").strip() or "student"

                if user_id:
                    duplicate = connection.execute(
                        "SELECT 1 FROM users WHERE username = ? AND id != ?",
                        (username, user_id),
                    ).fetchone()

                    if duplicate:
                        raise ValueError("Username already exists.")

                    if password:
                        connection.execute(
                            "UPDATE users SET username = ?, role = ?, password_hash = ? WHERE id = ?",
                            (username, role, self.hash_password(password), user_id),
                        )
                    else:
                        connection.execute(
                            "UPDATE users SET username = ?, role = ? WHERE id = ?",
                            (username, role, user_id),
                        )

                else:
                    existing = connection.execute(
                        "SELECT 1 FROM users WHERE username = ?",
                        (username,),
                    ).fetchone()

                    if existing:
                        raise ValueError("Username already exists.")

                    user_id = self._create_user_record(
                        connection, username, password, role
                    ).lastrowid

            if student_id:
                if self._exists_any(
                    "students",
                    {
                        "student_code": data["student_code"],
                        "roll_no": data["roll_no"],
                        "email": email,
                        "phone": phone,
                    },
                    exclude_id=student_id,
                ):
                    raise ValueError("Duplicate student found.")

                connection.execute(
                    """
                    UPDATE students
                    SET student_code = ?, full_name = ?, class_name = ?, section = ?,
                        roll_no = ?, email = ?, phone = ?, address = ?, user_id = ?
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
                return None

            else:
                student_code = data.get("student_code") or self.generate_student_code()
                if self._exists_any(
                    "students",
                    {
                        "student_code": student_code,
                        "roll_no": data["roll_no"],
                        "email": email,
                        "phone": phone,
                    },
                ):
                    raise ValueError("Duplicate student found.")

                cursor = connection.execute(
                    """
                    INSERT INTO students (
                        student_code, full_name, class_name, section,
                        roll_no, email, phone, address, user_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_code,
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

    def add_student(self, data, account=None):
        return self.save_student(data, None, account)

    def update_student(self, student_id, data, account=None):
        return self.save_student(data, student_id, account)

    def delete_student(self, student_id: int) -> None:
        with self._connection() as connection:
            student = connection.execute(
                "SELECT user_id FROM students WHERE id = ?",
                (student_id,),
            ).fetchone()
            if student and student["user_id"]:
                connection.execute(
                    "DELETE FROM users WHERE id = ?", (student["user_id"],)
                )
            connection.execute("DELETE FROM students WHERE id = ?", (student_id,))

    def fetch_students(
        self,
        search_text: str = "",
        search_field: str = "full_name",
        order_by: str = "full_name",
        ascending: bool = True,
    ) -> List[Dict[str, Any]]:
        allowed_fields = {"full_name", "student_code", "roll_no", "class_name"}
        allowed_order = {
            "student_code",
            "full_name",
            "class_name",
            "section",
            "roll_no",
            "email",
            "phone",
            "address",
            "join_date",
        }
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

    def issue_book(
        self, book_id: int, member_id: int, issue_date: Optional[str] = None
    ) -> int:
        issue_day = date.fromisoformat(issue_date) if issue_date else date.today()
        due_day = issue_day + timedelta(days=14)

        with self._connection() as connection:
            book = connection.execute(
                "SELECT id, available_quantity, reserved_quantity FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if not book:
                raise ValueError("Book not found.")

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

            existing_ready_member = connection.execute(
                """
                SELECT * from reservations
                WHERE book_id = ? and member_id=? and (status='Ready' or status='Active')
                """,
                (book["id"], member["id"]),
            ).fetchone()

            if (
                not existing_ready_member
                and int(book["available_quantity"]) - int(book["reserved_quantity"])
                <= 0
            ):
                raise ValueError("All available books have been reserved")

            if existing_ready_member:
                fulfilled_date = date.today()
                connection.execute(
                    "UPDATE reservations SET status='Fulfilled', fulfill_date=? WHERE id=?",
                    (fulfilled_date.isoformat(), existing_ready_member["id"]),
                )
                connection.execute(
                    "UPDATE books SET reserved_quantity=reserved_quantity-1 WHERE id=?",
                    (book["id"],),
                )

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

            self.next_reserve(issue["book_id"], connection)
        return fine

    def fetch_issued_books(
        self,
        order_by: str = "id",
        ascending: bool = True,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        allowed_order = {
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
        }
        order = order_by if order_by in allowed_order else "id"
        direction = "ASC" if ascending else "DESC"

        query = """
            SELECT
                issued_books.id AS id,
                issued_books.book_id AS book_id,
                issued_books.member_id AS member_id,
                issued_books.issue_date AS issue_date,
                issued_books.due_date AS due_date,
                issued_books.return_date AS return_date,
                issued_books.status AS status,
                issued_books.fine_amount AS fine_amount,
                books.book_code AS book_code,
                books.title AS title,
                books.author AS author,
                members.member_code AS member_code,
                members.name AS member_name,
                members.phone
            FROM issued_books
            JOIN books ON books.id = issued_books.book_id
            JOIN members ON members.id = issued_books.member_id
        """
        params: List[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += f" ORDER BY {order} {direction}"

        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def dashboard_stats(self) -> Dict[str, Any]:
        today = date.today().isoformat()
        with self._connection() as connection:
            total_books = connection.execute(
                "SELECT COALESCE(SUM(quantity), 0) AS total FROM books"
            ).fetchone()["total"]
            total_members = connection.execute(
                "SELECT COUNT(*) AS total FROM members"
            ).fetchone()["total"]
            total_students = connection.execute(
                "SELECT COUNT(*) AS total FROM students"
            ).fetchone()["total"]
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
            books_reserved = connection.execute(
                "SELECT COUNT(*) AS total FROM reservations WHERE status = 'Ready' OR status = 'Active'"
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
            "books_reserved": int(books_reserved),
            "overdue_books": int(overdue_books),
            "total_fines": float(total_fines),
        }

    def report_available_books(self) -> List[Dict[str, Any]]:
        return [
            book
            for book in self.fetch_books(order_by="title")
            if int(book["available_quantity"]) > 0
        ]

    def report_unavailable_books(self) -> List[Dict[str, Any]]:
        return [
            book
            for book in self.fetch_books(order_by="title")
            if int(book["available_quantity"]) - int(book["reserved_quantity"]) <= 0
        ]

    def report_issued_books(self) -> List[Dict[str, Any]]:
        return self.fetch_issued_books(status="Issued")

    def report_active_reservation(self) -> List[Dict[str, Any]]:
        return self.fetch_reservations(status="Active")

    def report_expired_reservation(self) -> List[Dict[str, Any]]:
        return self.fetch_reservations(status="Expired")

    def report_ready_reservation(self) -> List[Dict[str, Any]]:
        return self.fetch_reservations(status="Ready")

    def report_canceled_reservation(self) -> List[Dict[str, Any]]:
        return self.fetch_reservations(status="Canceled")

    def report_fulfill_reservation(self) -> List[Dict[str, Any]]:
        return self.fetch_reservations(status="Fulfilled")

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
            rows = connection.execute("""
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
                """).fetchall()
        return [dict(row) for row in rows]

    def get_library_settings(self) -> Dict[str, str]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT setting_key, setting_value FROM settings"
            ).fetchall()
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

    # ── Reservation Feature ──────────────────────────────────────────────────

    def add_reservation(
        self, book_id: int, member_id: int, reserved_date: Optional[str] = None
    ) -> int:
        """Reserve a book for a member. Expires automatically after 3 days."""
        res_day = date.fromisoformat(reserved_date) if reserved_date else date.today()
        # expiry_day = res_day + timedelta(days=3)
        with self._connection() as connection:
            book = connection.execute(
                "SELECT id, available_quantity, reserved_quantity FROM books WHERE id = ?",
                (book_id,),
            ).fetchone()
            if not book:
                raise ValueError("Book not found.")
            if int(book["available_quantity"]) > int(book["reserved_quantity"]):
                raise ValueError(
                    "Book is currently available — please issue it directly instead of reserving."
                )
            member = connection.execute(
                "SELECT id FROM members WHERE id = ?", (member_id,)
            ).fetchone()
            if not member:
                raise ValueError("Member not found.")

            existing_issue = connection.execute(
                "SELECT status FROM issued_books WHERE book_id=? AND member_id=? AND status='Issued' LIMIT 1",
                (book_id, member_id),
            ).fetchone()

            if existing_issue:
                raise ValueError("Member already issues this book")

            existing = connection.execute(
                "SELECT status FROM reservations WHERE book_id=? AND member_id=? AND (status='Active' OR status='Ready') LIMIT 1",
                (book_id, member_id),
            ).fetchone()
            if existing:
                if existing["status"] == "Active":
                    raise ValueError(
                        "Member already has an Active reservation for this book."
                    )
                else:
                    raise ValueError(
                        "The book is now available to issue for this member."
                    )

            all_reservations = connection.execute(
                "SELECT * FROM reservations WHERE book_id=? AND status='Active'",
                (book_id,),
            ).fetchall()

            queue_pos = len(all_reservations) + 1

            cursor = connection.execute(
                "INSERT INTO reservations (book_id, member_id, reserved_date, queue_pos, status) VALUES (?, ?, ?, ?, 'Active')",
                (book_id, member_id, res_day.isoformat(), queue_pos),
            )

            connection.execute(
                "UPDATE books SET reserved_quantity=reserved_quantity + 1 WHERE id=?",
                (book_id,),
            )

            return cursor.lastrowid

    def cancel_reservation(self, reservation_id: int) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, status, book_id, queue_pos FROM reservations WHERE id = ?",
                (reservation_id,),
            ).fetchone()
            if not row:
                raise ValueError("Reservation not found.")
            if row["status"] != "Active" and row["status"] != "Ready":
                raise ValueError("Only Active or Ready reservations can be cancelled.")
            connection.execute(
                "UPDATE reservations SET status='Canceled' WHERE id = ?",
                (reservation_id,),
            )
            connection.execute(
                "UPDATE books SET reserved_quantity=reserved_quantity - 1 WHERE id=?",
                (row["book_id"],),
            )

            if row["status"] == "Active":
                self.update_queue_pos(row["book_id"], row["queue_pos"], connection)
            else:
                self.next_reserve(row["book_id"], connection)

    def update_queue_pos(self, book_id: int, queue_pos: int, connection) -> None:

        rows = connection.execute(
            "SELECT * from reservations WHERE book_id=? and queue_pos>?",
            (book_id, queue_pos),
        ).fetchall()
        for row in rows:
            connection.execute(
                "UPDATE reservations SET queue_pos=queue_pos-1 WHERE id=?",
                (row["id"],),
            )

    def expire_reservations(self) -> int:
        """Mark all past-expiry Active reservations as Expired. Returns count updated."""
        today = date.today().isoformat()
        with self._connection() as connection:
            rows = connection.execute(
                """
			SELECT id, book_id
			FROM reservations
			WHERE status='Ready'
			AND expiry_date < ?
			""",
                (today,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE reservations
                    SET status='Expired'
                    WHERE id=?
                    """,
                    (row["id"],),
                )

                connection.execute(
                    """
                    UPDATE books
                    SET reserved_quantity=reserved_quantity-1
                    WHERE id=?
                    """,
                    (row["book_id"],),
                )

            return len(rows)

    def next_reserve(self, book_id, connection) -> bool:
        row = connection.execute(
            """SELECT id
            FROM reservations 
            WHERE status='Active' AND book_id=? AND queue_pos=1
        """,
            (book_id,),
        ).fetchone()

        if not row:
            return False

        ready_date = date.today()
        expiry_date = ready_date + timedelta(days=3)
        connection.execute(
            "UPDATE reservations SET queue_pos=0, status='Ready', ready_date=?, expiry_date=? where id=?",
            (
                ready_date.isoformat(),
                expiry_date.isoformat(),
                row["id"],
            ),
        )

        self.update_queue_pos(book_id, 1, connection)

        return True

    def change_queue_pos(self, current_position, new_position, book_code):
        if current_position == 1 and new_position == 0:
            raise ValueError("Cannot move first position to 0")

        query = """SELECT id, queue_pos 
            FROM reservations 
            WHERE status='Active' AND book_id=? AND (queue_pos=? OR queue_pos=?)
            ORDER BY queue_pos
        """
        with self._connection() as connection:
            book = connection.execute(
                "SELECT id FROM books WHERE book_code=?", (book_code,)
            ).fetchone()
            rows = connection.execute(
                query, (book["id"], current_position, new_position)
            ).fetchall()

            if len(rows) != 2:
                raise ValueError("Queue position is already lowest")

            res_a, res_b = rows

            if res_a["queue_pos"] == current_position:
                current_reservation = res_a
                swap_reservation = res_b
            else:
                current_reservation = res_b
                swap_reservation = res_a

            connection.execute(
                "UPDATE reservations SET queue_pos=? WHERE id=?",
                (new_position, current_reservation["id"]),
            )
            connection.execute(
                "UPDATE reservations SET queue_pos=? WHERE id=?",
                (current_position, swap_reservation["id"]),
            )

    def fetch_reservations(
        self,
        search_text: str = "",
        search_field: str = "id",
        order_by: str = "id",
        ascending: bool = True,
        status: Optional[str] = None,
    ) -> List[Dict]:
        allowed_fields = {
            "book_code",
            "title",
            "member_code",
            "member_name",
            "status",
        }

        allowed_order = {
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
        }

        field = search_field if search_field in allowed_fields else "title"

        order = order_by if order_by in allowed_order else "id"
        direction = "ASC" if ascending else "DESC"

        params: List[Any] = []
        query = """
            SELECT reservations.id AS id, 
                   reservations.reserved_date AS reserved_date, 
                   reservations.ready_date AS ready_date, 
                   reservations.expiry_date AS expiry_date, 
                   reservations.fulfill_date AS fulfill_date,
                   reservations.queue_pos AS queue_pos, 
                   reservations.status AS status,
                   books.book_code AS book_code, 
                   books.title AS title,
                   members.member_code AS member_code, 
                   members.name AS member_name
            FROM reservations
            JOIN books ON books.id = reservations.book_id
            JOIN members ON members.id = reservations.member_id
        """

        if search_text.strip():
            query += f" WHERE {field} LIKE ?"
            params.append(f"%{search_text.strip()}%")
            if status:
                query += "status = ?"
                params.append(status)
        else:
            if status:
                query += " WHERE status = ?"
                params.append(status)
        query += f" ORDER BY {order} {direction}"
        with self._connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_reservation_by_id(self, reservation_id: int) -> Optional[Dict]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT reservations.*, books.book_code, books.title,
                       members.member_code, members.name AS member_name
                FROM reservations
                JOIN books ON books.id = reservations.book_id
                JOIN members ON members.id = reservations.member_id
                WHERE reservations.id = ?
            """,
                (reservation_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_reservations_by_book_id(self, book_id: int) -> Optional[Dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT reservations.*, books.book_code, books.title,
                       members.member_code, members.name AS member_name
                FROM reservations
                JOIN books ON books.id = reservations.book_id
                JOIN members ON members.id = reservations.member_id
                WHERE reservations.book_id = ?
            """,
                (book_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_ready_reservation_by_book_id(self, book_id: int) -> Optional[Dict]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM reservations
                WHERE book_id = ? and status='Ready'?
            """,
                (book_id,),
            ).fetchone()
        return dict(row) if row else None
