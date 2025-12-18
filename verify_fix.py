import requests
import sys
import time

BASE_URL = "http://127.0.0.1:8888"


def check_status():
    url = f"{BASE_URL}/api/actions/status"
    try:
        print(f"Checking {url}...")
        response = requests.get(url, timeout=2)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json())
            return True
        else:
            print("Failed: Status not 200")
            print(response.text)
            return False
    except requests.exceptions.ConnectionError:
        print("Failed to connect. Is the server running?")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_charts():
    url = f"{BASE_URL}/api/charts/list"
    try:
        print(f"\nChecking {url}...")
        response = requests.get(url, timeout=2)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} companies")
            if len(data) > 0:
                print("First item sample:", data[0].get("code"), data[0].get("name"))
                return True
            else:
                print("Warning: List is empty. Check data files.")
                return False
        else:
            print("Failed: Status not 200")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    status_ok = check_status()
    charts_ok = check_charts()

    if status_ok and charts_ok:
        print("\nSUCCESS: All checks passed.")
    else:
        print("\nFAILURE: Some checks failed.")
        sys.exit(1)
