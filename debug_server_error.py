import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from python.web.routes.charts import list_charts


async def run_debug():
    print("Function imported. Running list_charts()...")
    try:
        result = await list_charts()
        print("Success!")
        print(f"Result count: {len(result)}")
        # print(result[:1])
    except Exception as e:
        print("\n❌ CAUGHT EXCEPTION:")
        print(e)
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_debug())
