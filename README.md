# MiniMart — FastAPI Online Shopping App

A beginner-friendly shopping application built with Python, FastAPI, SQLAlchemy, SQLite, Jinja2, HTML and CSS.

## Features
- Product catalogue and search
- Product details
- Cookie-based shopping cart
- Checkout and order confirmation
- Stock validation and stock updates
- Basic product CRUD endpoints
- SQLite database created automatically

## Run locally

Create a virtual environment:

**Windows PowerShell**
```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

**Linux / macOS / WSL**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. Interactive API docs: http://127.0.0.1:8000/docs

## Project structure
```text
minimart/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── templates/
│   └── static/
├── requirements.txt
├── .gitignore
└── README.md
```

## Important
This is a learning/demo project. Before production use, add authentication and authorization for admin routes, CSRF protection, stronger validation, database migrations, payment integration, and production security settings. This app does not collect real payments.