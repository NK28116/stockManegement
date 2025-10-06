import pandas as pd
from python.db.database import get_portfolio_data
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("portfolioテーブルのデータを取得します。")
    df_portfolio = get_portfolio_data()

    if not df_portfolio.empty:
        logger.info("portfolioテーブルの内容:")
        print(df_portfolio.to_string())
    else:
        logger.info("portfolioテーブルにデータがありません。")
