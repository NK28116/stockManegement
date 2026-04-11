from python.db.database import engine, Base
from python.db.models import Portfolio

# テーブルを一度削除してから再作成
print("Dropping and recreating portfolio table...")
Portfolio.__table__.drop(engine, checkfirst=True)
Portfolio.__table__.create(engine, checkfirst=True)
print("Done!")
