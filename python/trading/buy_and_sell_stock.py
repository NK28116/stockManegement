#!/usr/bin/env python3
import argparse
import os
from datetime import datetime

import pandas as pd

from python.config import config

try:
    import yfinance as yf
except Exception:
    yf = None

__all__ = [
    "load_codes",
    "save_codes",
    "get_price",
    "buy",
    "sell",
    "refresh_prices",
    "get_name",
    "fix_names",
    "pre_buy",
    "main",
]


def load_codes(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"ファイルがありません: {path}")
    df = pd.read_csv(path)
    expected = [
        "code",
        "name",
        "quantity",
        "purchase_price",
        "purchase_date",
        "sector",
        "status",
    ]
    # 余分な列は残しつつ、最低限の列がなければ補完
    for col in expected:
        if col not in df.columns:
            if col in ["name", "sector", "purchase_date", "status", "code"]:
                df[col] = ""
            elif col == "quantity":
                df[col] = 0
            elif col == "purchase_price":
                df[col] = 0.0
    # 型整形
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    df["purchase_price"] = pd.to_numeric(df["purchase_price"], errors="coerce").fillna(0.0)
    return df


def save_codes(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"更新完了: {os.path.relpath(path, os.path.dirname(__file__))}")


def get_price(code: str) -> float:
    if yf is None:
        return 0.0
    try:
        t = yf.Ticker(code)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 0.0


def buy(df: pd.DataFrame, code: str, qty: int, price: float | None) -> pd.DataFrame:
    today = datetime.now().strftime("%Y-%m-%d")
    idx = df.index[df["code"] == code]
    if price is None:
        price = get_price(code)
    if len(idx) == 0:
        # 新規行
        df.loc[len(df)] = {
            "code": code,
            "name": get_name(code),
            "quantity": qty,
            "purchase_price": float(price) if price else 0.0,
            "purchase_date": today,
            "sector": "",
        }
        if "status" in df.columns:
            df.loc[len(df) - 1, "status"] = "保有中"
    else:
        i = idx[0]
        old_q = int(df.at[i, "quantity"])
        old_p = float(df.at[i, "purchase_price"])
        new_q = old_q + qty
        if new_q <= 0:
            # 全部売却の形になった場合は0で保持
            df.at[i, "quantity"] = 0
            if "status" in df.columns:
                df.at[i, "status"] = "売却済"
            df = df.drop(idx).reset_index(drop=True) # 保有数が0になったら行を削除
        else:
            # 加重平均は購入時（qty > 0）のみ計算
            if qty > 0 and price and old_q > 0:
                new_p = (old_q * old_p + qty * float(price)) / new_q
            elif qty > 0 and price and old_q == 0:
                new_p = float(price)
            else:
                new_p = old_p
            df.at[i, "quantity"] = new_q
            df.at[i, "purchase_price"] = round(new_p, 2)
            if "status" in df.columns:
                df.at[i, "status"] = "保有中"
        # 購入日は初回のまま残す（必要なら更新: df.at[i,"purchase_date"]=today）
    action = "買い" if qty > 0 else "売り"
    sign = "+" if qty > 0 else ""
    message = f"{action}: {code} {sign}{qty}株 @¥{price if price else 'N/A'}"
    print(message)
    from python.utils.alert import send_alert

    send_alert(message, level="INFO")
    return df


def sell(df: pd.DataFrame, code: str, qty: int) -> pd.DataFrame:
    idx = df.index[df["code"] == code]
    if len(idx) == 0:
        print(f"エラー: {code} はmy_stock.csvに存在しません")
        return df
    i = idx[0]
    cur_q = int(df.at[i, "quantity"])
    if qty > cur_q:
        print(f"エラー: 売却数量が保有数を超えています (保有 {cur_q}株)")
        return df
    new_q = cur_q - qty
    df.at[i, "quantity"] = new_q
    if new_q == 0:
        if "status" in df.columns:
            df.at[i, "status"] = "売却済"
        # 平均取得単価はそのまま保持（必要なら0にする: df.at[i,"purchase_price"]=0.0）
        df = df.drop(idx).reset_index(drop=True) # 保有数が0になったら行を削除
    else:
        if "status" in df.columns:
            df.at[i, "status"] = "保有中"
    message = f"売り: {code} -{qty}株（残 {new_q}株）"
    print(message)
    from python.utils.alert import send_alert

    send_alert(message, level="INFO")
    return df


# 価格更新用: yfinanceで現在値と損益を更新
def refresh_prices(df: pd.DataFrame, target_code: str | None = None) -> pd.DataFrame:
    if not {"purchase_price", "quantity"}.issubset(df.columns):
        return df
    from datetime import datetime

    updated = df.copy()
    now_str = datetime.now().strftime("%Y-%m-%d")
    for i, row in updated.iterrows():
        code = str(row.get("code", "")).strip()
        if not code:
            continue
        if target_code and code != target_code:
            continue
        cur = get_price(code)
        if "current_price" in updated.columns:
            updated.at[i, "current_price"] = round(cur, 2)
        qty = int(row.get("quantity", 0) or 0)
        pp = float(row.get("purchase_price", 0.0) or 0.0)
        if "profit_loss" in updated.columns:
            updated.at[i, "profit_loss"] = round((cur - pp) * qty, 2)
        if "profit_loss_percent" in updated.columns:
            updated.at[i, "profit_loss_percent"] = "{((cur-pp)/pp*100):+.2f}%" if pp > 0 else "0.00%"
        if "last_updated" in updated.columns:
            updated.at[i, "last_updated"] = now_str
    return updated


# 追加
def get_name(code: str) -> str:
    if yf is None:
        return code
    try:
        t = yf.Ticker(code)
        info = {}
        try:
            info = t.get_info()  # yfinance>=0.2
        except Exception:
            info = getattr(t, "info", {}) or {}
        name = info.get("shortName") or info.get("longName") or info.get("symbol")
        return str(name) if name else code
    except Exception:
        return code


# 追加: 既存レコードのnameを補完
def fix_names(df: pd.DataFrame) -> pd.DataFrame:
    updated = df.copy()
    for i, row in updated.iterrows():
        code = str(row.get("code", "")).strip()
        name = str(row.get("name", "")).strip()
        if not code:
            continue
        if (not name) or (name == code):
            updated.at[i, "name"] = get_name(code)
    return updated


def pre_buy(df: pd.DataFrame, code: str, qty: int, price: float | None) -> pd.DataFrame:
    today = datetime.now().strftime("%Y-%m-%d")
    idx = df.index[df["code"] == code]
    qty = 1
    if price is None:
        price = get_price(code)
    if len(idx) == 0:
        # 新規行
        df.loc[len(df)] = {
            "code": code,
            "name": get_name(code),
            "quantity": qty,
            "purchase_price": float(price) if price else 0.0,
            "purchase_date": today,
            "sector": "",
            "status": "監視中",
        }
    else:
        i = idx[0]
        if df.at[i, "status"] == "監視中":
            # 既存の監視中があれば更新
            df.at[i, "quantity"] = qty
            df.at[i, "purchase_price"] = float(price) if price else 0.0
            df.at[i, "purchase_date"] = today
        else:
            # 既存の保有株とは別に新規行として追加
            df.loc[len(df)] = {
                "code": code,
                "name": df.at[i, "name"],
                "quantity": qty,
                "purchase_price": float(price) if price else 0.0,
                "purchase_date": today,
                "sector": df.at[i, "sector"],
                "status": "監視中",
            }
    message = f"監視中: {code} ({qty}株あたり) @¥{price if price else 'N/A'}"
    print(message)
    from python.utils.alert import send_alert

    send_alert(message, level="INFO")
    return df


def main():
    parser = argparse.ArgumentParser(description="my_stock.csvの売買操作ツール")
    sub = parser.add_subparsers(dest="action", required=True)

    p_buy = sub.add_parser("buy")
    p_buy.add_argument("code")
    p_buy.add_argument("quantity", type=int)
    p_buy.add_argument("--price", type=float, default=None)

    # 監視中用のパーサーを追加
    p_prebuy = sub.add_parser("prebuy")
    p_prebuy.add_argument("code")
    p_prebuy.add_argument("quantity", type=int)
    p_prebuy.add_argument("--price", type=float, default=None)

    p_sell = sub.add_parser("sell")
    p_sell.add_argument("code")
    p_sell.add_argument("quantity", type=int)

    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("code", nargs="?", help="特定銘柄のみ更新（省略時は全銘柄）")

    args = parser.parse_args()

    df = load_codes(config.codes_path)

    if args.action == "buy":
        df = buy(df, args.code, args.quantity, getattr(args, "price", None))
    elif args.action == "prebuy":
        df = pre_buy(df, args.code, args.quantity, getattr(args, "price", None))
    elif args.action == "sell":
        df = sell(df, args.code, args.quantity)
    elif args.action == "refresh":
        df = refresh_prices(df, getattr(args, "code", None))
    elif args.action == "fixnames":
        df = fix_names(df)

    save_codes(df, config.codes_path)


if __name__ == "__main__":
    main()
