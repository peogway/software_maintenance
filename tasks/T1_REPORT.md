# Code Comprehension Report

## 1. High-Level Architecture

The system is a single-process, fully offline desktop application built on 
<br>

**Python 3 / Tkinter / SQLite3**.
<p align="center">
	<img src="./diagrams/high-level-architecture.png" alt="High-level Architecture">
</p>

<br>

**Layers:**

| Layer | Responsibility |
|---|---|
| `main.py` | Application bootstrap, window lifecycle, routing |
| `modules/base.py` | Shared constants (COLORS, FONTS) and reusable widget helpers |
| `modules/*.py` (UI) | One Tkinter Frame per domain, each self-contained |
| `modules/database.py` | All SQL logic; returns plain `dict` objects to the UI |

---

## 2. Class Diagram

<p align="center">
	<img src="./diagrams/class_diagram.png" alt="Class Diagram">
</p>

---

## 3. Sequence Diagram 

<p align="center">
	<img src="./diagrams/sequence_diagram.png" alt="Sequence Diagram">
</p>


---

## 4. Dependency Graph

<p align="center">
	<img src="./diagrams/dependency_graph.png" alt="Sequence Diagram">
</p>


---
