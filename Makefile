SHELL := /bin/bash

BACKEND_DIR := backend
ADMIN_DIR := admin
MOBILE_DIR := mobile

-include $(BACKEND_DIR)/.env
-include $(BACKEND_DIR)/.env.local
-include $(ADMIN_DIR)/.env
-include $(ADMIN_DIR)/.env.local
-include $(MOBILE_DIR)/.env
-include $(MOBILE_DIR)/.env.local
-include .env
-include .env.local

LAN_HOST := $(shell hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^192\.168\.0\.' | head -n 1)
BACKEND_HOST ?= $(or $(HOST),$(APP_HOST),$(LAN_HOST),0.0.0.0)
BACKEND_BIND_HOST ?= 0.0.0.0
ADMIN_HOST ?= $(or $(HOST),$(APP_HOST),$(BACKEND_HOST))
BACKEND_PORT ?= 8005
ADMIN_PORT ?= 3005
API_BASE_URL ?= http://127.0.0.1:$(BACKEND_PORT)
METRO_HOST ?= 0.0.0.0
METRO_PORT ?= 8085
TEST_BACKEND_PORT ?= 28005
TEST_ADMIN_PORT ?= 23005
TEST_METRO_PORT ?= 28085
GRADLE_USER_HOME ?= /tmp/forgemind-gradle
UV_CACHE_DIR ?= /tmp/forgemind-uv-cache
UV ?= $(if $(wildcard $(BACKEND_DIR)/.venv/bin/uv),.venv/bin/uv,uv)

.PHONY: help setup setup-backend setup-admin setup-mobile infra infra-down migrate backend backend-test-server frontend frontend-test-server admin mobile mobile-test-server android-tunnel android-install test test-backend test-admin test-mobile audit clean

help:
	@echo "ForgeMind commands"
	@echo "  make setup         Install backend, admin, and mobile dependencies"
	@echo "  make infra         Start Postgres, Prometheus, and Grafana"
	@echo "  make infra-down    Stop Docker Compose services"
	@echo "  make migrate       Run backend database migrations"
	@echo "  make backend       Run FastAPI on http://$(BACKEND_BIND_HOST):$(BACKEND_PORT)"
	@echo "  make backend-test-server Run FastAPI test server on http://$(BACKEND_BIND_HOST):$(TEST_BACKEND_PORT)"
	@echo "  make frontend      Run admin dashboard on http://$(ADMIN_HOST):$(ADMIN_PORT)"
	@echo "  make frontend-test-server Run admin test server on http://$(ADMIN_HOST):$(TEST_ADMIN_PORT)"
	@echo "  make mobile        Start React Native Metro on http://$(METRO_HOST):$(METRO_PORT)"
	@echo "  make mobile-test-server Start Metro test server on http://$(METRO_HOST):$(TEST_METRO_PORT)"
	@echo "  make android-tunnel Forward Android device Metro port over USB"
	@echo "  make android-install Install the mobile app on a connected Android device"
	@echo "  make test          Run backend tests and TS checks"
	@echo "  make audit         Run production dependency audits"
	@echo "  BACKEND_BIND_HOST=0.0.0.0 controls backend listener"
	@echo "  BACKEND_HOST=192.168.0.106 controls public API URL used by admin"
	@echo "  API_BASE_URL=http://192.168.0.106:8005 controls mobile backend URL"
	@echo "  ADMIN_HOST=192.168.0.106 controls admin listener"
	@echo "  Test ports: backend $(TEST_BACKEND_PORT), admin $(TEST_ADMIN_PORT), metro $(TEST_METRO_PORT)"

setup: setup-backend setup-admin setup-mobile

setup-backend:
	cd $(BACKEND_DIR) && UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync

setup-admin:
	cd $(ADMIN_DIR) && npm install

setup-mobile:
	cd $(MOBILE_DIR) && npm install

infra:
	docker compose up -d postgres prometheus grafana

infra-down:
	docker compose down

migrate:
	cd $(BACKEND_DIR) && UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run alembic upgrade head

backend:
	cd $(BACKEND_DIR) && UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run uvicorn app.main:app --reload --host $(BACKEND_BIND_HOST) --port $(BACKEND_PORT)

backend-test-server:
	cd $(BACKEND_DIR) && UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run uvicorn app.main:app --reload --host $(BACKEND_BIND_HOST) --port $(TEST_BACKEND_PORT)

frontend: admin

admin:
	cd $(ADMIN_DIR) && NEXT_PUBLIC_API_BASE_URL=http://$(BACKEND_HOST):$(BACKEND_PORT) npx next dev -H $(ADMIN_HOST) -p $(ADMIN_PORT)

frontend-test-server:
	cd $(ADMIN_DIR) && NEXT_PUBLIC_API_BASE_URL=http://$(BACKEND_HOST):$(TEST_BACKEND_PORT) npx next dev -H $(ADMIN_HOST) -p $(TEST_ADMIN_PORT)

mobile:
	cd $(MOBILE_DIR) && npm run start -- --host $(METRO_HOST) --port $(METRO_PORT)

mobile-test-server:
	cd $(MOBILE_DIR) && npm run start -- --host $(METRO_HOST) --port $(TEST_METRO_PORT)

android-tunnel:
	adb reverse tcp:$(METRO_PORT) tcp:$(METRO_PORT)
	adb reverse tcp:$(BACKEND_PORT) tcp:$(BACKEND_PORT)

android-install: android-tunnel
	cd $(MOBILE_DIR) && API_BASE_URL=$(API_BASE_URL) GRADLE_USER_HOME=$(GRADLE_USER_HOME) npm run android -- --port $(METRO_PORT) --no-packager

test: test-backend test-admin test-mobile

test-backend:
	cd $(BACKEND_DIR) && UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run pytest tests

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
