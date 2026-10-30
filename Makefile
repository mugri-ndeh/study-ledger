# make setup          -> install Python and Node dependencies (once)
# make db             -> start only Postgres (in Docker), for development and tests
# make dev            -> API on :8000 with reload + Vite UI on :5173 (open http://localhost:5173); needs `make db`
# make up             -> build and run everything in Docker (open http://localhost:8000)
# make test           -> backend tests against the ledger_test database
# make import-sqlite EMAIL=you@example.com -> copy the old backend/data/learning.db into a new account
# make backup         -> dump the Postgres database into backups/

# Load POSTGRES_PASSWORD etc. from .env for the local commands.
ifneq (,$(wildcard .env))
include .env
export
endif

PY = backend/.venv/bin/python

setup:
	@test -f .env || (cp .env.example .env && sed -i '' "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$$(python3 -c 'import secrets;print(secrets.token_urlsafe(18))')/" .env && echo "Created .env")
	python3.13 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

db:
	docker compose up -d --wait db
	@docker compose exec -T db psql -U ledger -d ledger -tc "SELECT 1 FROM pg_database WHERE datname = 'ledger_test'" | grep -q 1 \
		|| docker compose exec -T db psql -U ledger -d ledger -c "CREATE DATABASE ledger_test"

migrate:
	cd backend && .venv/bin/alembic upgrade head && .venv/bin/python -m cli bootstrap

dev: migrate
	@trap 'kill 0' EXIT; \
	(cd backend && .venv/bin/uvicorn main:app --reload --port 8000) & \
	(cd frontend && npm run dev)

up:
	docker compose up -d --build --wait
	@echo "Running at http://localhost:8000"

test:
	cd backend && .venv/bin/python -m pytest -q

import-sqlite:
	@test -n "$(EMAIL)" || (echo "Usage: make import-sqlite EMAIL=you@example.com" && exit 1)
	docker compose exec app python -m cli import-sqlite /import/learning.db --email "$(EMAIL)" --name "$(or $(NAME),Me)" --admin

backup:
	@mkdir -p backups
	docker compose exec -T db pg_dump -U ledger -d ledger --format=custom > backups/ledger-$$(date +%Y%m%d-%H%M).dump
	@echo "Saved to backups/ (restore with: docker compose exec -T db pg_restore -U ledger -d ledger --clean < FILE)"

.PHONY: setup db migrate dev up test import-sqlite backup
