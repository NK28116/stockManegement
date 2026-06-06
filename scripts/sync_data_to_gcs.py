import os
import sys
import glob
import subprocess


def run_command(cmd):
    """Executes a shell command."""
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")


def clear_gcs_prefix(bucket_name: str, prefix: str):
    """GCS上の指定prefix配下を削除（現ポートフォリオに無い古い画像を一掃）。"""
    uri = f"gs://{bucket_name}/{prefix}**"
    print(f"Clearing stale objects under: gs://{bucket_name}/{prefix}")
    # 対象が空のときはエラーになり得るが、run_command 側で握りつぶして続行する
    run_command(["gcloud", "storage", "rm", uri])


def sync_to_gcs(period: str = "1mo"):
    """
    ローカルで生成したチャートを、UIが参照するGCSパスへ同期する。
      - data/plots/<period>/*.png   -> charts/indicators/<file>
      - data/chartImg/<period>/*.png -> charts/signals/<file>
    生成物は period サブディレクトリ配下に出るため、glob も period を含める。
    同期前に GCS 側の古いチャートをクリアし、現ポートフォリオ分のみ残す。
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME", "stock-management-494305-prod")
    print(f"Starting sync to GCS bucket: {bucket_name} (period={period})")

    # 古いチャートを一掃してから現行分をアップロード
    clear_gcs_prefix(bucket_name, "charts/signals/")
    clear_gcs_prefix(bucket_name, "charts/indicators/")

    # Mappings: Local Path -> GCS Path
    files_to_sync = [
        ("data/my_stock.csv", "my_stock.csv"),
        ("data/latest_indicators.json", "latest_indicators.json"),
    ]

    # Plots (indicators) -> charts/indicators/
    for p in glob.glob(f"data/plots/{period}/*.png"):
        files_to_sync.append((p, f"charts/indicators/{os.path.basename(p)}"))

    # ChartImg (signals) -> charts/signals/
    for p in glob.glob(f"data/chartImg/{period}/*.png"):
        files_to_sync.append((p, f"charts/signals/{os.path.basename(p)}"))

    print(f"Found {len(files_to_sync)} files to upload.")

    for local_path, remote_path in files_to_sync:
        if not os.path.exists(local_path):
            print(f"Skipping missing file: {local_path}")
            continue

        gcs_uri = f"gs://{bucket_name}/{remote_path}"
        # Use 'gcloud storage cp' (content-type は拡張子から自動判定)
        cmd = ["gcloud", "storage", "cp", local_path, gcs_uri]
        run_command(cmd)

    print("Sync completed.")


if __name__ == "__main__":
    # 期間は引数 or 環境変数 CHART_PERIOD、デフォルト 1mo
    period_arg = sys.argv[1] if len(sys.argv) > 1 else os.getenv("CHART_PERIOD", "1mo")
    sync_to_gcs(period_arg)
