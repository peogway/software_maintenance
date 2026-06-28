# New Feature: Book Reservations

### Stakeholder Request

> "When all copies of a book are checked out, members need a way to queue up for the next available copy instead of having to keep checking manually."
---
### Design

A new `reservations` table was added to SQLite:

```sql
CREATE TABLE IF NOT EXISTS reservations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    member_id       INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    reserved_date   TEXT NOT NULL,
    ready_date      TEXT DEFAULT NULL,
    expiry_date     TEXT DEFAULT NULL,    -- auto-set to reserved_date + 3 days
    fulfill_date    TEXT DEFAULT NULL,
    queue_pos       INTEGER DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'Active',  -- Active|Ready|Cancelled|Expired|Fulfilled
);
```
---
### Business Rules

| Rule | Implementation |
|---|---|
| Only books with no available copies can be reserved | `add_reservation()` checks `available_quantity > reserved_quantity` and blocks reservation if copies are available |
| One active/ready reservation per member per book | `add_reservation()` prevents duplicate reservations with status `Active` or `Ready` |
| Members cannot reserve books they already borrowed | `add_reservation()` checks `issued_books` for `status='Issued'` |
| Reservations are queued | New reservation gets `queue_pos = active reservations + 1` |
| First waiting reservation becomes ready when a copy is available | `next_reserve()` changes first `Active` reservation (`queue_pos=1`) to `Ready` |
| Ready reservations expire after 3 days | `next_reserve()` sets `expiry_date = ready_date + 3 days`; `expire_reservations()` changes overdue reservations to `Expired` |
| Book return automatically processes next reservation | `return_book()` calls `next_reserve()` |
| Issuing a reserved book automatically fulfills reservation | `issue_book()` updates reservation status to `Fulfilled` and stores `fulfill_date` |
| Reserved quantity is adjusted automatically | Reservation fulfillment, cancellation, and expiration update `reserved_quantity` |
| Members without reservations cannot issue fully reserved books | `issue_book()` blocks issue if all copies are reserved |
| Cancelling reservation updates queue order | `cancel_reservation()` updates queue positions |
| Queue positions can be manually swapped | `change_queue_pos()` swaps queue positions |
| Reservation statuses | `Active`, `Ready`, `Fulfilled`, `Expired`, `Canceled` |

---
### Modified Methods

- `issue_book()` — after inserting into issued_books, automatically fulfils any matching Active/Ready reservation (sets status = Fulfilled, stores fulfill_date)
- `return_book()` — after returning a book, automatically calls next_reserve() to promote next queued reservation to Ready
- `_initialize_database()` — includes CREATE TABLE IF NOT EXISTS reservations schema

---

### New Database Methods

```python
# Reservation methods

def add_reservation(
	book_id: int,
	member_id: int,
	reserved_date: Optional[str] = None
) -> int:
	pass


def cancel_reservation(
	reservation_id: int
) -> None:
	pass


def expire_reservations() -> int:
	pass


def next_reserve(
	book_id: int,
	connection
) -> bool:
	pass


def change_queue_pos(
	current_position: int,
	new_position: int,
	book_code: str
) -> None:
	pass


def fetch_reservations(
	search_text: str = "",
	search_field: str = "id",
	order_by: str = "id",
	ascending: bool = True,
	status: Optional[str] = None
) -> List[Dict]:
	pass


def get_reservation_by_id(
	reservation_id: int
) -> Optional[Dict]:
	pass


def get_reservations_by_book_id(
	book_id: int
) -> Optional[List[Dict]]:
	pass


def get_ready_reservation_by_book_id(
	book_id: int
) -> Optional[Dict]:
	pass
```
---
