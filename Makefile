.PHONY: install install-python infra-up infra-down web api worker lint format test smoke

install:
	npm install

install-python:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

infra-up:
	docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml up -d

infra-down:
	docker compose --env-file infra/docker/.env -f infra/docker/docker-compose.yml down

web:
	npm run web:dev

api:
	uvicorn services.api.app.main:app --host 0.0.0.0 --port $${API_PORT:-8010} --reload

worker:
	celery -A services.workers.app.celery_app:celery_app worker --loglevel=info

lint:
	npm run lint
	python3 -m ruff check .

format:
	npm run format
	python3 -m ruff format --check .

test:
	python3 -m pytest

smoke:
	./scripts/smoke/startup-smoke.sh
