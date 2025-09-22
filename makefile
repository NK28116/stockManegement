# Makefile for Stock Management System

# Variables
PYTHON = python3
PYTHONPATH = ${PWD}

WATCH_DIR = python/watch
ANALYSIS_DIR = python/analysis
DB_DIR = python/db
LOG_DIR = log

PYTHON_WATCH_MODULES =python.watch
PYTHON_ANALYSIS_MODULES =python.analysis
PYTHON_DB_MODULES =python.db
PYTHON_UTIL_MODULES =python.utils
PYTHON_TRADING_MODULES =python.trading
PYTHON_VISUALIZATION_MODULES =python.visualization

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
	@echo ""
	@echo "Windows Specific:"
	@echo "  create-win-batch  Generate run_watch.bat for Windows auto-startup"
	@echo "  run-win-batch     Test the generated run_watch.bat"

# Watch Module
.PHONY: watch-dev
watch-dev:
ifndef DATE
	$(error Please specify a date with DATE=YYYYMMDD for development mode)
endif
	@echo "Starting watch in development mode for date: ${DATE}..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -m ${WATCH_DIR}.watch --dev ${DATE}

.PHONY: watch-realtime
watch-realtime:
	@echo "Starting real-time monitoring..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -m ${WATCH_DIR}.watch

# Analysis
.PHONY: analyze
analyze:
	@echo "Running analysis for all stocks..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -m ${WATCH_DIR}.analyze

.PHONY: analyze-stock
analyze-stock:
ifndef CODE
	$(error Please specify stock code with CODE=your_stock_code)
endif
	@echo "Running analysis for stock: ${CODE}"
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -c "from python.watch.analyze import analyze_daily_data; analyze_daily_data('${CODE}')"

.PHONY: aggregate
aggregate:
	@echo "Running daily aggregation..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -m ${WATCH_DIR}.dailyAggregator

# Database
.PHONY: init-db
init-db:
	@echo "Initializing database..."
	@mkdir -p ${DB_DIR}
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} -c "from python.init_database import init_database; init_database()"

.PHONY: backup-db
backup-db:
	@echo "Creating database backup..."
	@mkdir -p ${DB_DIR}/backups
	@cp ${DB_DIR}/my_stock.db ${DB_DIR}/backups/my_stock_$(shell date +%Y%m%d_%H%M%S).db

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
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} main.py daily
	@echo "Daily tasks completed."

.PHONY: run-weekly
run-weekly: backup-db
	@echo "Running weekly tasks..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} main.py weekly
	@echo "Weekly tasks completed."

.PHONY: run-monthly
run-monthly: backup-db
	@echo "Running monthly tasks..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} main.py monthly
	@echo "Monthly tasks completed."

.PHONY: run-yearly
run-yearly: backup-db
	@echo "Running yearly tasks..."
	@PYTHONPATH=${PYTHONPATH} ${PYTHON} main.py yearly
	@echo "Yearly tasks completed."

# スケジュール設定 (crontab用)
.PHONY: install-cron
install-cron:
	@echo "Installing cron jobs..."
	@(crontab -l 2>/dev/null; \
	  echo "# Stock Management System - Daily tasks (9:00 AM on weekdays)"; \
	  echo "0 9 * * 1-5 cd /mnt/e/doc/git/PrivateDevelop/stockManegement && ${PYTHON} main.py daily > ${LOG_DIR}/cron_daily.log 2>&1"; \
	  echo ""; \
	  echo "# Weekly tasks (Saturday 10:00 AM)"; \
	  echo "0 10 * * 6 cd /mnt/e/doc/git/PrivateDevelop/stockManegement && ${PYTHON} main.py weekly > ${LOG_DIR}/cron_weekly.log 2>&1"; \
	  echo ""; \
	  echo "# Monthly tasks (1st day of month at 11:00 AM)"; \
	  echo "0 11 1 * * cd /mnt/e/doc/git/PrivateDevelop/stockManegement && ${PYTHON} main.py monthly > ${LOG_DIR}/cron_monthly.log 2>&1"; \
	  echo ""; \
	  echo "# Yearly tasks (January 1st at 12:00 PM)"; \
	  echo "0 12 1 1 * cd /mnt/e/doc/git/PrivateDevelop/stockManegement && ${PYTHON} main.py yearly > ${LOG_DIR}/cron_yearly.log 2>&1") | crontab -
	@echo "Cron jobs installed. Current crontab:"
	@crontab -l


# Windows 用: 自動起動バッチ作成
create-win-batch:
	@echo @echo off > run_watch.bat
	@echo cd /d ${PWD} >> run_watch.bat
	@echo ${PYTHON} main.py watch-realtime >> run_watch.bat
	@echo "✅ run_watch.bat を作成しました。スタートアップにショートカットを置いてください。"
	@echo "# Note: This batch file is also updated automatically via GitHub Actions on each push to keep Windows deployment in sync."

# Windows 用: バッチ実行確認
run-win-batch:
	@cmd /c run_watch.bat
