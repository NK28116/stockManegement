# Makefile for Stock Management System

# Variables
PYTHON = venv/bin/python
PYTHON_CRON={PYTHONPATH_GCE}/${PYTHON} 
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
	@echo "  assets          Rebuild static CSS/JS under python/web/static (needs Node.js)"
	@echo "  env             Generate .env from Bitwarden via chezmoi (see Docs/SECRETS_BITWARDEN.md)"
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
	@echo "PostgreSQL database backup should be handled via pg_dump or cloud usage."
	@echo "See python/db/dump_csv.py for archiving data."

# Development
.PHONY: install
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
	@if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

.PHONY: test
test:
	@echo "Running tests..."
	@PYTHONPATH=. pytest tests/

# 画面の静的アセット (Tailwind CSS / Vue) を再生成する。
# テンプレートや画面で使う Tailwind クラスを変更したら実行し、成果物をコミットする。
.PHONY: assets
assets:
	@cd frontend && npm ci && npm run build

# Bitwarden の項目から .env を生成する (chezmoi と Bitwarden CLI が必要 / Docs/SECRETS_BITWARDEN.md)。
# 既存の .env は .env.bak に退避する。失敗したときは既存の .env を変更しない。
.PHONY: env
env:
	@command -v chezmoi >/dev/null || { echo "chezmoi が見つかりません (brew install chezmoi)"; exit 1; }
	@command -v bw >/dev/null || { echo "Bitwarden CLI (bw) が見つかりません (brew install bitwarden-cli)"; exit 1; }
	@umask 077; chezmoi execute-template < .env.chezmoi.tmpl > .env.tmp || { rm -f .env.tmp; echo ".env の生成に失敗しました"; exit 1; }
	@if [ -f .env ]; then cp .env .env.bak && chmod 600 .env.bak; fi
	@mv .env.tmp .env && chmod 600 .env && echo ".env を生成しました (前の内容は .env.bak)"

# DB スキーマと Alembic 履歴の整合を確認する (読み取り専用 / PRIDEV-487)
.PHONY: db-check
db-check:
	@echo "Checking DB schema consistency..."
	@PYTHONPATH=. python -m python.db.schema_check

# マイグレーションを最新まで適用する
.PHONY: db-upgrade
db-upgrade:
	@echo "Applying migrations..."
	@PYTHONPATH=. python -m alembic upgrade head

.PHONY: lint
lint:
	@echo "Running linter..."
	@flake8 python/

.PHONY: format
format:
	@echo "Formatting code..."
	@black python/
	@isort python/

.PHONY: check-format
check-format:
	@echo "Checking code format..."
	@black --check python/
	@isort --check-only python/

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

# スケジュール設定 (crontab用).PHONY: install-cron
install-cron:
	@echo "Installing cron jobs..."
	@(crontab -l 2>/dev/null; \
	  echo "# Daily Monitor Report (9:00 AM weekdays)"; \
	  echo "0 9 * * 1-5 cd <PROJECT_ROOT> && source venv/bin/activate && <PROJECT_ROOT>/venv/bin/python main.py daily > <PROJECT_ROOT>/cron_daily_morning.log  2>&1"; \
	  echo "# Daily Evening Report (4:00 PM weekdays)"; \
	  echo "0 16 * * 1-5 cd <PROJECT_ROOT> && source venv/bin/activate && <PROJECT_ROOT>/venv/bin/python main.py daily  && gcloud storage cp <PROJECT_ROOT>/data gs://<GCS_BUCKET_NAME>/ --recursive && gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.txt --content-type='text/plain; charset=utf-8'&& gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.csv --content-type='text/csv; charset=utf-8'&& gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.png --content-type="image/png" && <PROJECT_ROOT>/scripts/send_report.sh daily> <PROJECT_ROOT>/cron_daily_evening.log 2>&1"; \
	  echo "# Weekly tasks (Saturday 10:00 AM)"; \
	  echo "0 10 * * 6 cd <PROJECT_ROOT> && source venv/bin/activate && <PROJECT_ROOT>/venv/bin/python main.py weekly  && gcloud storage cp <PROJECT_ROOT>/data gs://<GCS_BUCKET_NAME>/ --recursive && gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.txt --content-type='text/plain; charset=utf-8'&& gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.csv --content-type='text/csv; charset=utf-8' && gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.png --content-type="image/png" && <PROJECT_ROOT>/scripts/send_report.sh weekly> <PROJECT_ROOT>/cron_weekly.log 2>&1"; \
	  echo "# Monthly tasks (1st day 10:00 AM)"; \
	  echo "0 10 1 * * cd <PROJECT_ROOT> && source venv/bin/activate && <PROJECT_ROOT>/venv/bin/python main.py monthly  && gcloud storage cp <PROJECT_ROOT>/data gs://<GCS_BUCKET_NAME>/ --recursive && gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.txt --content-type='text/plain; charset=utf-8'&& gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.csv --content-type='text/csv; charset=utf-8' && gcloud storage objects update gs://<GCS_BUCKET_NAME>/**/*.png --content-type="image/png" && <PROJECT_ROOT>/scripts/send_report.sh monthly> <PROJECT_ROOT>/cron_monthly.log 2>&1"; \
	  echo "# Yearly tasks (Jan 1, 12:00 PM)"; \
	  echo "0 12 1 1 * cd <PROJECT_ROOT> && source venv/bin/activate && <PROJECT_ROOT>/venv/bin/python main.py yearly > <PROJECT_ROOT>/cron_yearly.log 2>&1" \
	) | crontab -
	@echo "Cron jobs installed. Current crontab:"
	@crontab -l
