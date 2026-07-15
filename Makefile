SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help setup up up-polling down logs migrate superuser backend-check frontend-check check test build

help:
	@printf "FlatHunter AI commands:\n"
	@printf "  make setup          Copy .env.example to .env\n"
	@printf "  make up             Start the web stack\n"
	@printf "  make up-polling     Start the web stack and Telegram polling bot\n"
	@printf "  make check          Run backend and frontend quality gates\n"
	@printf "  make test           Run all automated tests\n"
	@printf "  make build          Build production artifacts\n"

setup:
	@test -f .env || cp .env.example .env

up:
	docker compose up --build -d

up-polling:
	docker compose --profile polling up --build -d

down:
	docker compose --profile polling down

logs:
	docker compose logs -f --tail=150

migrate:
	docker compose exec backend uv run --no-sync python manage.py migrate

superuser:
	docker compose exec backend uv run --no-sync python manage.py createsuperuser

backend-check:
	cd backend && uv run --no-sync ruff format --check apps config tests manage.py
	cd backend && uv run --no-sync ruff check apps config tests manage.py
	cd backend && uv run --no-sync mypy apps config
	cd backend && uv run --no-sync pytest

frontend-check:
	cd miniapp && npm run lint
	cd miniapp && npm run typecheck
	cd miniapp && npm test
	cd miniapp && npm run build

check: backend-check frontend-check

test:
	cd backend && uv run --no-sync pytest
	cd miniapp && npm test

build:
	docker compose build backend miniapp
