.PHONY: setup backend frontend data test build

setup:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && python scripts/generate_mock_data.py
	cd frontend && npm install

data:
	cd backend && . .venv/bin/activate && python scripts/generate_mock_data.py

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

test:
	cd backend && . .venv/bin/activate && pytest -q

build:
	cd frontend && npm run build
