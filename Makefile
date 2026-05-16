SHELL := /bin/bash

BACKEND_DIR := backend
ADMIN_DIR := admin
MOBILE_DIR := mobile
LAN_HOST := $(shell hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^192\.168\.0\.' | head -n 1)
HOST ?= $(or $(APP_HOST),$(LAN_HOST),0.0.0.0)
BACKEND_PORT ?= 8005
ADMIN_PORT ?= 3005
METRO_HOST ?= 0.0.0.0
METRO_PORT ?= 8085
TEST_BACKEND_PORT ?= 28005
TEST_ADMIN_PORT ?= 23005
TEST_METRO_PORT ?= 28085
GRADLE_USER_HOME ?= /tmp/forgemind-gradle
PYTHON := $(BACKEND_DIR)/.venv/bin/python
PIP := $(BACKEND_DIR)/.venv/bin/pip
UVICORN := $(BACKEND_DIR)/.venv/bin/uvicorn
ALEMBIC := $(BACKEND_DIR)/.venv/bin/alembic

.PHONY: help setup setup-backend setup-admin setup-mobile infra infra-down migrate backend backend-test-server frontend frontend-test-server admin mobile mobile-test-server android-tunnel android-install test test-backend test-admin test-mobile audit clean

help:
	@echo "ForgeMind commands"
	@echo "  make setup         Install backend, admin, and mobile dependencies"
	@echo "  make infra         Start Postgres, Prometheus, and Grafana"
	@echo "  make infra-down    Stop Docker Compose services"
	@echo "  make migrate       Run backend database migrations"
	@echo "  make backend       Run FastAPI on http://$(HOST):$(BACKEND_PORT)"
	@echo "  make backend-test-server Run FastAPI test server on http://$(HOST):$(TEST_BACKEND_PORT)"
	@echo "  make frontend      Run admin dashboard on http://$(HOST):$(ADMIN_PORT)"
	@echo "  make frontend-test-server Run admin test server on http://$(HOST):$(TEST_ADMIN_PORT)"
	@echo "  make mobile        Start React Native Metro on http://$(METRO_HOST):$(METRO_PORT)"
	@echo "  make mobile-test-server Start Metro test server on http://$(METRO_HOST):$(TEST_METRO_PORT)"
	@echo "  make android-tunnel Forward Android device Metro port over USB"
	@echo "  make android-install Install the mobile app on a connected Android device"
	@echo "  make test          Run backend tests and TS checks"
	@echo "  make audit         Run production dependency audits"
	@echo "  HOST=192.168.0.x can override auto-detected LAN host"
	@echo "  Test ports: backend $(TEST_BACKEND_PORT), admin $(TEST_ADMIN_PORT), metro $(TEST_METRO_PORT)"

setup: setup-backend setup-admin setup-mobile

setup-backend:
	test -d $(BACKEND_DIR)/.venv || python3 -m venv $(BACKEND_DIR)/.venv
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt

setup-admin:
	cd $(ADMIN_DIR) && npm install

setup-mobile:
	cd $(MOBILE_DIR) && npm install

infra:
	docker compose up -d postgres prometheus grafana

infra-down:
	docker compose down

migrate:
	cd $(BACKEND_DIR) && .venv/bin/alembic upgrade head

backend:
	cd $(BACKEND_DIR) && .venv/bin/uvicorn app.main:app --reload --host $(HOST) --port $(BACKEND_PORT)

backend-test-server:
	cd $(BACKEND_DIR) && .venv/bin/uvicorn app.main:app --reload --host $(HOST) --port $(TEST_BACKEND_PORT)

frontend: admin

admin:
	cd $(ADMIN_DIR) && NEXT_PUBLIC_API_BASE_URL=http://$(HOST):$(BACKEND_PORT) npx next dev -H $(HOST) -p $(ADMIN_PORT)

frontend-test-server:
	cd $(ADMIN_DIR) && NEXT_PUBLIC_API_BASE_URL=http://$(HOST):$(TEST_BACKEND_PORT) npx next dev -H $(HOST) -p $(TEST_ADMIN_PORT)

mobile:
	cd $(MOBILE_DIR) && npm run start -- --host $(METRO_HOST) --port $(METRO_PORT)

mobile-test-server:
	cd $(MOBILE_DIR) && npm run start -- --host $(METRO_HOST) --port $(TEST_METRO_PORT)

android-tunnel:
	adb reverse tcp:$(METRO_PORT) tcp:$(METRO_PORT)

android-install: android-tunnel
	cd $(MOBILE_DIR) && GRADLE_USER_HOME=$(GRADLE_USER_HOME) npm run android -- --port $(METRO_PORT) --no-packager

test: test-backend test-admin test-mobile

test-backend:
	$(PYTHON) -m pytest $(BACKEND_DIR)/tests

test-admin:
	cd $(ADMIN_DIR) && npm run typecheck

test-mobile:
	cd $(MOBILE_DIR) && npm run typecheck

audit:
	cd $(ADMIN_DIR) && npm audit --omit=dev
	cd $(MOBILE_DIR) && npm audit --omit=dev

clean:
	rm -rf $(BACKEND_DIR)/.pytest_cache
	rm -rf $(ADMIN_DIR)/.next $(ADMIN_DIR)/tsconfig.tsbuildinfo
	rm -rf $(MOBILE_DIR)/tsconfig.tsbuildinfo
