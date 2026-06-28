# Testing & Test Coverage
---

## 1. Test Structure

- **Unit tests** → `test_unit_database.py`
- **Integration tests** → `test_integration.py`
- **Regression tests** → `test_regression.py`
- **Fixtures** → `conftest.py`


## 2. Pytest configuration (`pytest.ini`)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short

```

For running tests:
```bash
pip install pytest pytest-cov

pytest tests/ --cov=modules.database --cov-report=term-missing
```

## 3. Unit Tests
**File:** `test_unit_database.py`

### Purpose
Tests individual functions in isolation.

### Coverage
- Password hashing & verification
- Code generation (book/member/student)
- Book CRUD operations
- Member CRUD operations
- User authentication & management
- Fine calculation logic
- Dashboard statistics
- Library settings

### Examples of tested behavior
- Same salt → same hash
- Wrong password fails authentication
- Book creation returns valid ID
- Available quantity initializes correctly
- Fine = 10 per overdue day
- Duplicate email/phone rejected
- Issued books cannot be deleted

---

## 4. Integration Tests
**File:** `test_integration.py`

### Scenario 1 — Full Book Lifecycle
Flow:
- Add book
- Add member
- Issue book
- Check overdue state
- Return book with fine
- Verify dashboard stats
- Check overdue report
- Full CRUD cycle (add → search → update → delete)

### Scenario 2 — Reservation Queue Lifecycle
Flow:
- Book fully issued
- Members join reservation queue
- Queue ordering maintained
- Return triggers “Ready” state
- Issue reserved book → fulfilled
- Cancel reservation updates queue
- Expired reservation handled
- Duplicate reservation blocked

---

## 5. Regression Tests
**File:** `test_regression.py`

### Purpose
Prevents previously known bugs from reappearing.

### REG-001: Code Generation
- Ensures codes are always generated from max value
- Prevents accidental reuse of deleted IDs

### REG-002: Inventory Safety
- Prevents available quantity going below 0
- Blocks issuing more books than available

### REG-003: Fine Report Accuracy
- Only positive fines included
- Zero-fine records excluded

### REG-004: Settings Idempotency
- Update behaves like UPSERT
- No duplicate settings entries

### REG-005: Search & Ordering Safety
- Rejects unsafe SQL-like input
- Falls back to safe defaults
- Validates ordering logic

### REG-006: Student–User Linkage
- Creating student can create user account
- Deleting student deletes linked user
- Prevents duplicate usernames

### REG-007: Reservation State Rules
- Only valid reservation transitions allowed
- Prevents reservation if already issued

---

## 6. Test Fixtures
**File:** `conftest.py`

### db fixture
- Fresh isolated database per test
- Uses temporary file per test

### db_with_data fixture
Preloaded state:
- 1 book (Clean Code)
- 1 member (Alice Smith)
- 1 student (Bob Jones)

---

## 7. Coverage Summary

| Layer | Purpose | Coverage |
|------|--------|----------|
| Unit Tests | Core logic validation | High |
| Integration Tests | Workflow validation | High |
| Regression Tests | Bug prevention | High |

### Overall Coverage
- Total coverage: **74%**
- File: `modules/database.py`
- Stmts: 545
- Missed: 141


---

## 8. Summary
This test suite ensures:
- Correct individual function behavior
- Stable end-to-end workflows
- Protection against old bugs
- Safe refactoring and future development