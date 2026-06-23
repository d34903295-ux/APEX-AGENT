.PHONY: help install run test lint paper up down logs clean

help:
	@echo "APEX-AGENT PRO"
	@echo "  make install   install python deps"
	@echo "  make run       run all-in-one orchestrator (paper mode)"
	@echo "  make test      run the test suite"
	@echo "  make up        docker compose up (full distributed stack)"
	@echo "  make down      docker compose down"
	@echo "  make logs      tail compose logs"

install:
	pip install -r requirements.txt

run:
	python -m apex.main

paper:
	APEX_MODE=paper APEX_LIVE_TRADING_ENABLED=false python -m apex.main

test:
	pytest -q

lint:
	ruff check apex tests || true

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
