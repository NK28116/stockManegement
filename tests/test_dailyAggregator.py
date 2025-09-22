import sqlite3
import pandas as pd
import tempfile
from python.watch import dailyAggregator


def test_aggregate_intraday_to_daily():
    # 一時DBを作成
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        dailyAggregator.DB_PATH = tmp.name

        conn = sqlite3.connect(tmp.name)
        c = conn.cursor()
        c.execute(
            """
        CREATE TABLE intraday (
            code TEXT,
            timestamp TEXT,
            price REAL,
            volume INTEGER
        )
        """
        )
        c.executemany(
            "INSERT INTO intraday VALUES (?, ?, ?, ?)",
            [
                ("7203.T", "2025-09-17 09:00:00", 2000, 100),
                ("7203.T", "2025-09-17 10:00:00", 2100, 150),
                ("7203.T", "2025-09-17 15:00:00", 2050, 200),
            ],
        )
        conn.commit()
        conn.close()

        # 実行
        dailyAggregator.aggregate_intraday_to_daily("2025-09-17")

        # 結果確認
        conn = sqlite3.connect(tmp.name)
        df = pd.read_sql_query("SELECT * FROM stock_data", conn)
        df["volume"] = df["volume"].apply(lambda x: int.from_bytes(x, "little") if isinstance(x, bytes) else x)

        conn.close()

        assert df.iloc[0]["open"] == 2000
        assert df.iloc[0]["high"] == 2100
        assert df.iloc[0]["low"] == 2000
        assert df.iloc[0]["close"] == 2050
        assert df.iloc[0]["volume"] == 450
