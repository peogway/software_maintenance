# Follow-up Report

## 1. Project Links
- GitHub repository: [Github link](https://github.com/peogway/software_maintenance)
- Demo video: [Demo video link](https://youtu.be/BbNpkuFae2o)

---


## 2. Work Completed

### T1 — Design & Analysis
- Created system documentation (class diagram, sequence diagrams, dependency graph)
- Defined layered architecture (UI, database layer, controller)

***More detailed:*** [T1_REPORT.md](T1_REPORT.md)

---

### T2 — Refactoring
- Removed duplicated database logic
- Introduced reusable functions:
  - code generation
  - record fetching and saving
  - form handling in UI
- Improved naming conventions
- Improved UI consistency using shared helpers

***More detailed:*** [T2_REPORT.md](T2_REPORT.md)



### T3 — New Feature (Reservations System)
- Implemented reservation system
- Added queue-based reservations
- Added auto “Ready” promotion
- Added expiry handling (3 days)
- Integrated reservations into issue/return flow
- Added reservation state management and queue control

***More detailed:*** [T3_REPORT.md](T3_REPORT.md)

---

### T4 — Testing
- Built pytest suite:
  - unit tests
  - integration tests
  - regression tests
- Coverage: 74%
- Verified workflows:
  - issue/return cycle
  - reservation pipeline
  - CRUD operations
  - authentication and fines


***More detailed:*** [T4_REPORT.md](T4_REPORT.md)

---

## 3. Evaluation of Contribution

The main goal was improving the existing system without changing user-facing behavior.

### Refactoring outcome
- Codebase made more consistent and easier to follow
- Removed repeated patterns in database and UI layers
- Reduced duplication in:
  - form handling
  - table setup
  - database queries
- Logic moved into shared helper functions

### Feature integration outcome
- Reservation feature integrated into existing system design
- Works with existing issue/return workflow
- Extends inventory rules instead of replacing them
- Queue logic fits into current system structure

### Testing outcome
- Tests ensured stability during changes
- Existing behavior preserved after refactoring
- Reservation flow covered with integration tests
- Regression tests prevent previously fixed issues from returning

### Overall result
- System is cleaner and more structured
- Codebase is easier to maintain
- New feature integrates smoothly into existing workflow

---

## 4. Demo Overview

- Show existing system features
- Demonstrate refactored UI consistency
- Show reservation queue flow
- Run tests and coverage report