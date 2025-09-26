# Makefile for Stock Management System

# Variables
PYTHON = venv/bin/python
PYHTON_CRON={PYTHONPATH_GCE}/${PYTHON} 
LOG_DIR = log

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help:
	@echo "Stock Management System - Available commands:"
	@echo ""
	@echo "Watch Module:"
	@echo "  watch-dev       Run watch.py in development mode with a specific date (e.g., make watch-dev DATE=20250115)"
	@echo "  watch-realtime  Run watch.py in real-time monitoring mode"
	@echo ""
	@echo "Analysis:"
	@echo "  analyze         Run analysis for all stocks in watchlist"
	@echo "  analyze-stock   Run analysis for a specific stock (set CODE=your_stock_code)"
	@echo "  aggregate       Run daily aggregation of watch data"
	@echo ""
	@echo "Database:"
	@echo "  init-db         Initialize the database"
	@echo "  backup-db       Create a backup of the database"
	@echo ""
	@echo "Development:"
	@echo "  install         Install all dependencies"
	@echo "  test            Run tests"
	@echo "  lint            Run code linter"
	@echo "  format          Format code using black and isort"
	@echo "  clean           Clean up temporary files"
	@echo ""
	@echo "Automation:"
	@echo "  run-daily       Execute daily tasks via main.py"
	@echo "  run-weekly      Execute weekly tasks via main.py"
	@echo "  run-monthly     Execute monthly tasks via main.py"
	@echo "  run-yearly      Execute yearly tasks via main.py"
	@echo "  install-cron    Install scheduled tasks with cron"

# Watch Module
.PHONY: watch-dev
watch-dev:
ifndef DATE
	$(error Please specify a date with DATE=YYYYMMDD for development mode)
endif
	@echo "Starting watch in development mode for date: ${DATE}..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} python/watch/watch.py --dev ${DATE}

.PHONY: watch-realtime
watch-realtime:
	@echo "Starting real-time monitoring..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} python/watch/watch.py

# Analysis
.PHONY: analyze
analyze:
	@echo "Running analysis for all stocks..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} python/watch/analyze.py

.PHONY: analyze-stock
analyze-stock:
ifndef CODE
	$(error Please specify stock code with CODE=your_stock_code)
endif
	@echo "Running analysis for stock: ${CODE}"
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} -c "from python.watch.analyze import analyze_daily_data; analyze_daily_data('${CODE}')"

.PHONY: aggregate
aggregate:
	@echo "Running daily aggregation..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} python/watch/dailyAggregator.py

# Database
.PHONY: init-db
init-db:
	@echo "Initializing database..."
	@mkdir -p data/db
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} python/init_database.py

.PHONY: backup-db
backup-db:
	@echo "Creating database backup..."
	@mkdir -p data/db/backups
	@cp data/db/my_stock.db data/db/backups/my_stock_$(shell date +%Y%m%d_%H%M%S).db

# Development
.PHONY: install
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt

.PHONY: test
test:
	@echo "Running tests..."
	@pytest tests/

.PHONY: lint
lint:
	@echo "Running linter..."
	@flake8 python/

.PHONY: format
format:
	@echo "Formatting code..."
	@black python/
	@isort python/

.PHONY: clean
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -r {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".DS_Store" -delete
	@echo "Done!"

# 定期実行タスク (main.py経由)
.PHONY: run-daily
run-daily: backup-db
	@echo "Running daily tasks..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} main.py daily > ${LOG_DIR}/cron_daily.log 2>&1
	@echo "Daily tasks completed."

.PHONY: run-weekly
run-weekly: backup-db
	@echo "Running weekly tasks..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} main.py weekly > ${LOG_DIR}/cron_weekly.log 2>&1
	@echo "Weekly tasks completed."

.PHONY: run-monthly
run-monthly: backup-db
	@echo "Running monthly tasks..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} main.py monthly > ${LOG_DIR}/cron_monthly.log 2>&1
	@echo "Monthly tasks completed."

.PHONY: run-yearly
run-yearly: backup-db
	@echo "Running yearly tasks..."
	@PYTHONPATH_GCE=${PYTHONPATH_GCE}/${PYTHON} main.py yearly > ${LOG_DIR}/cron_yearly.log 2>&1
	@echo "Yearly tasks completed."

# スケジュール設定 (crontab用)
.PHONY: install-cron
install-cron:
	@echo "Installing cron jobs..."
	@(crontab -l 2>/dev/null; \
	  echo "# Stock Management System - Daily Monitor Report (9:00 AM on weekdays)"; \
	  echo "0 9 * * 1-5 cd ${PWD} && ${PYHTON_CRON} main.py daily > ${LOG_DIR}/cron_daily_morning.log 2>&1"; \
	  echo ""; \
	  echo "# Stock Management System - Daily Evening Report (5:00 PM on weekdays)"; \
	  echo "0 17 * * 1-5 cd ${PWD} &&${PYHTON_CRON} main.py daily > ${LOG_DIR}/cron_daily_evening.log 2>&1"; \
	  echo ""; \
	  echo "# Weekly tasks (Saturday 10:00 AM)"; \
	  echo "0 10 * * 6 cd ${PWD} && ${PYHTON_CRON} main.py weekly > ${LOG_DIR}/cron_weekly.log 2>&1"; \
	  echo ""; \
	  echo "# Monthly tasks (1st day of month at 11:00 AM)"; \
	  echo "0 11 1 * * cd ${PWD} && ${PYHTON_CRON} main.py monthly > ${LOG_DIR}/cron_monthly.log 2>&1"; \
	  echo ""; \
	  echo "# Yearly tasks (January 1st at 12:00 PM)"; \
	  echo "0 12 1 1 * cd ${PWD} && ${PYHTON_CRON} main.py yearly > ${LOG_DIR}/cron_yearly.log 2>&1") | crontab -
	@echo "Cron jobs installed. Current crontab:"
	@crontab -l
