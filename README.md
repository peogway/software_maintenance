# Library Management System

A fully offline desktop Library Management System built with Python 3, Tkinter, and SQLite3.

## Features

- Secure login with hashed passwords
- Dashboard with live summary cards
- Book management with add, update, delete, search, and sorting
- Member management with add, update, delete, search, and sorting
- Student management with add, update, delete, search, and sorting
- Issue and return workflow with automatic due dates and fines
- Reports for available books, issued books, overdue books, members, students, and fines
- CSV export for reports
- Admin-only user management for staff accounts and roles
- Library settings and password change support
- SQLite backup and restore tools
- Automatic book codes in the format `BK0001`, `BK0002`, ...
- Automatic member codes in the format `MB0001`, `MB0002`, ...
- Automatic student codes in the format `ST0001`, `ST0002`, ...

## Environment Setup

Create and activate a virtual environment:

```bash
# windows
python -m venv venv

# mac/linux
python3 -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

If Tkinter is missing on Linux, install it first:

```bash
sudo apt install python3-tk
```

## Requirements

The project uses:

- Python 3
- Tkinter
- SQLite3
- Pillow

## Database Information

The database is created automatically at startup in:

- `database/library.db`

Tables created automatically:

- `users`
- `books`
- `members`
- `students`
- `issued_books`
- `settings`

Default admin account:

- Username: `admin`
- Password: `admin123`

Passwords are stored using PBKDF2 hashing.

## Project Structure

```text
library_management_system/
├── backup/
├── assets/
│   ├── logo.png
│   └── icons/
├── database/
│   └── library.db
├── modules/
│   ├── base.py
│   ├── database.py
│   ├── login.py
│   ├── dashboard.py
│   ├── books.py
│   ├── members.py
│   ├── students.py
│   ├── issue_books.py
│   ├── reports.py
│   ├── users.py
│   └── settings.py
├── requirements.txt
├── main.py
└── README.md
```

## Usage Guide

- Start the application with `python main.py`.
- Log in with the default admin account the first time.
- Use the sidebar to open Books, Members, Students, Issue Books, Reports, Users, and Settings.
- Backup creates a copy of the database inside the `backup/` folder.
- Restore replaces the current database with a selected backup file.

## Fine Rules

- Up to 14 days: no fine
- After the due date: 10 taka per day

## Screenshots

Add screenshots here after running the application.

- Login screen: `screenshots/login.png`
- Dashboard: `screenshots/dashboard.png`
- Books module: `screenshots/books.png`
- Members module: `screenshots/members.png`
- Students module: `screenshots/students.png`
- Issue books module: `screenshots/issue_books.png`
- Reports module: `screenshots/reports.png`
- Users module: `screenshots/users.png`
- Settings module: `screenshots/settings.png`

## Notes

- The application runs fully offline.
- SQLite is the only database engine used.
- A custom `assets/logo.png` file is optional. If it is missing, the app shows a fallback logo.
