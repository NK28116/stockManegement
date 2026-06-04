import os
import glob
import subprocess


def run_command(cmd):
    """Executes a shell command."""
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")


def sync_to_gcs():
    """
    Synchronizes local data to the GCS bucket defined by GCS_BUCKET_NAME using gcloud CLI.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME", "stock-management-494305-prod")
    print(f"Starting sync to GCS bucket: {bucket_name}")

    # Mappings: Local Path -> GCS Path
    files_to_sync = [
        ("data/my_stock.csv", "my_stock.csv"),
        ("data/latest_indicators.json", "latest_indicators.json"),
    ]

    # Add Plots
    local_plots = glob.glob("data/plots/*.png")
    for p in local_plots:
        filename = os.path.basename(p)
        files_to_sync.append((p, f"charts/indicators/{filename}"))

    # Add ChartImg
    local_chart_imgs = glob.glob("data/chartImg/*.png")
    for p in local_chart_imgs:
        filename = os.path.basename(p)
        files_to_sync.append((p, f"charts/signals/{filename}"))

    print(f"Found {len(files_to_sync)} files to upload.")

    for local_path, remote_path in files_to_sync:
        if not os.path.exists(local_path):
            print(f"Skipping missing file: {local_path}")
            continue

        gcs_uri = f"gs://{bucket_name}/{remote_path}"
        # Use 'gcloud storage cp'
        cmd = ["gcloud", "storage", "cp", local_path, gcs_uri]
        run_command(cmd)

    print("Sync completed.")


if __name__ == "__main__":
    sync_to_gcs()
