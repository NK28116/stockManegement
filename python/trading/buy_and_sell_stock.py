#!/usr/bin/env python3
import argparse
import os
from datetime import datetime

import pandas as pd
from psycopg2 import Error as PgError

from python.config import config
from python.db.database import get_db_connection

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
        "purpose",  # sectorをpurposeに置き換え
        "status",
    ]
    # 余分な列は残しつつ、最低限の列がなければ補完
    for col in expected:
        if col not in df.columns:
            if col in [
                "name",
                "purpose",
                "purchase_date",
                "status",
                "code",
            ]:  # sectorをpurposeに置き換え
                df[col] = ""
            elif col == "quantity":
                df[col] = 0
            elif col == "purchase_price":
                df[col] = 0.0
    # 型整形
    # 既存の'sector'カラムを'purpose'にリネーム、または削除
    if "sector" in df.columns:
        if "purpose" not in df.columns:
            df = df.rename(columns={"sector": "purpose"})
            print("CSVヘッダー: 'sector' を 'purpose' にリネームしました。")
        else:
            # 'purpose'が既に存在する場合は'sector'を削除
            df = df.drop(columns=["sector"])
            print(
                "CSVヘッダー: 'sector' カラムを削除しました（'purpose'が既に存在するため）。"
            )

    df["quantity"] = (
        pd.to_numeric(df["quantity"], errors="coerce").fillna(0).astype(int)
    )
    df["purchase_price"] = pd.to_numeric(df["purchase_price"], errors="coerce").fillna(
        0.0
    )
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
            "purpose": "",  # sectorをpurposeに置き換え
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
                df.at[i, "status"] = "売却"
            df = df.drop(idx).reset_index(drop=True)  # 保有数が0になったら行を削除
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


def add_transaction(
    code: str, trade_type: str, quantity: int, price: float, trade_date: str
):
    """
    取引履歴をtransactionsテーブルに追加する
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # stocksテーブルに銘柄が存在しない場合は追加
        cur.execute(
            "INSERT INTO stocks (code, name, purpose) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING",
            (code, get_name(code), ""),
        )  # purposeは空で追加

        cur.execute(
            """
            INSERT INTO transactions (code, trade_type, quantity, price, trade_date)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (code, trade_type, quantity, price, trade_date),
        )
        conn.commit()
        print(
            f"取引履歴を追加しました: {trade_type} {code} {quantity}株 @¥{price} on {trade_date}"
        )
    except PgError as e:
        print(f"❌ 取引履歴追加エラー: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def sell_stock(code: str, sell_type: str) -> dict:
    """
    Sell a stock and update its status.
    This is intended to be called from the API.
    """
    path = config.codes_path
    try:
        df = load_codes(path)
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}

    idx = df.index[df["code"] == code]
    if len(idx) == 0:
        return {"error": f"Stock code {code} not found."}

    i = idx[0]
    quantity_to_sell = int(df.at[i, "quantity"])

    if quantity_to_sell <= 0:
        return {"error": f"No quantity to sell for {code}."}

    # Set status based on sell_type
    if sell_type == "profit":
        status = "売却（利益確定）"
    elif sell_type == "loss":
        status = "売却（損切り）"
    else:
        return {"error": "Invalid sell_type specified. Must be 'profit' or 'loss'."}

    df.at[i, "quantity"] = 0
    df.at[i, "status"] = status

    # Optional: You might want to remove the row from the active portfolio view
    # For now, we keep it with 0 quantity and a sold status.

    save_codes(df, path)

    message = f"Sold: {code} ({quantity_to_sell} shares) - Status: {status}"
    print(message)
    # from python.utils.alert import send_alert
    # send_alert(message, level="INFO")

    return {"message": message}


def sell(
    df: pd.DataFrame, code: str, qty: int, profit_loss_status: str | None = None
) -> pd.DataFrame:
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
            if profit_loss_status in ["売却（利益確定）", "売却（損切り）"]:
                df.at[i, "status"] = profit_loss_status
            else:
                df.at[i, "status"] = "売却"
        # 平均取得単価はそのまま保持（必要なら0にする: df.at[i,"purchase_price"]=0.0）
        df = df.drop(idx).reset_index(drop=True)  # 保有数が0になったら行を削除
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

    # 有効なステータスリスト
    valid_statuses = [
        "監視中",
        "保有中",
        "次回のスイングで購入",
        "売却（利益確定）",
        "売却（損切り）",
        "除外",
    ]

    rows_to_keep = []
    for i, row in updated.iterrows():
        code = str(row.get("code", "")).strip()
        if not code:
            continue
        if target_code and code != target_code:
            rows_to_keep.append(row)  # ターゲット外の銘柄はそのまま残す
            continue

        qty = int(row.get("quantity", 0) or 0)
        status = str(row.get("status", "")).strip()

        # quantityが0で、かつ有効な売却みステータスではない場合は削除対象
        # ただし、'除外'ステータスはquantityが0でなくても残す可能性があるため、別途考慮
        if qty == 0 and status not in [
            "売却（利益確定）",
            "売却（損切り）",
            "除外",
        ]:
            print(
                f"銘柄 {code} は保有数が0で、かつ有効な売却みステータスではないため削除します。"
            )
            continue  # この行はrows_to_keepに追加しない

        # statusが有効なリストに含まれていない場合も削除対象
        if status and status not in valid_statuses:
            print(f"銘柄 {code} のステータス '{status}' は無効なため削除します。")
            continue  # この行はrows_to_keepに追加しない

        cur = get_price(code)
        if "current_price" in updated.columns:
            row["current_price"] = round(cur, 2)

        pp = float(row.get("purchase_price", 0.0) or 0.0)
        if "profit_loss" in updated.columns:
            row["profit_loss"] = round((cur - pp) * qty, 2)
        if "profit_loss_percent" in updated.columns:
            row["profit_loss_percent"] = (
                f"{((cur-pp)/pp*100):+.2f}%" if pp > 0 else "0.00%"
            )
        if "last_updated" in updated.columns:
            row["last_updated"] = now_str

        rows_to_keep.append(row)

    updated = pd.DataFrame(rows_to_keep)
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
            "purpose": "",  # sectorをpurposeに置き換え
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
                "purpose": df.at[i, "purpose"],  # sectorをpurposeに置き換え
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
    p_buy.add_argument(
        "--purpose", type=str, default=None, help="present / middle / long / swing"
    )

    # 監視中用のパーサーを追加
    p_prebuy = sub.add_parser("prebuy")
    p_prebuy.add_argument("code")
    # quantityはpre_buy関数内で固定されるため、コマンドライン引数からは削除
    p_prebuy.add_argument("--price", type=float, default=None)
    p_prebuy.add_argument(
        "--purpose", type=str, default=None, help="present / middle / long / swing"
    )

    # --watch と --get は排他的な引数
    status_group = p_prebuy.add_mutually_exclusive_group()
    status_group.add_argument(
        "--watch", action="store_true", help="ステータスを '監視中' に設定"
    )
    status_group.add_argument(
        "--get", action="store_true", help="ステータスを '次回のスイングで購入' に設定"
    )
    # --status 引数は --watch / --get と同時に指定できないようにする
    status_group.add_argument(
        "--status",
        type=str,
        choices=[
            "監視中",
            "保有中",
            "次回のスイングで購入",
            "売却（利益確定）",
            "売却（損切り）",
            "除外",
        ],
        help="ステータスを直接指定",
    )

    p_sell = sub.add_parser("sell")
    p_sell.add_argument("code")
    p_sell.add_argument("quantity", type=int)
    p_sell.add_argument(
        "--profit_loss_status",
        type=str,
        default=None,
        help="売却（利益確定） / 売却（損切り）",
    )

    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("code", nargs="?", help="特定銘柄のみ更新（省略時は全銘柄）")

    sub.add_parser("csv-check")

    p_csv_edit = sub.add_parser("csv-edit")
    p_csv_edit.add_argument("code")
    p_csv_edit.add_argument(
        "--status",
        type=str,
        choices=[
            "監視中",
            "保有中",
            "次回のスイングで購入",
            "売却（利益確定）",
            "売却（損切り）",
            "除外",
        ],
        help="ステータスを選択",
    )
    p_csv_edit.add_argument(
        "--purpose",
        type=str,
        choices=["present", "middle", "long", "swing"],
        help="目的を選択",
    )

    p_add_transaction = sub.add_parser("add_transaction", help="過去の取引履歴を追加")
    p_add_transaction.add_argument("code", help="銘柄コード")
    p_add_transaction.add_argument(
        "trade_type", choices=["buy", "sell"], help="取引タイプ (buy または sell)"
    )
    p_add_transaction.add_argument("quantity", type=int, help="数量")
    p_add_transaction.add_argument("price", type=float, help="取引価格")
    p_add_transaction.add_argument("trade_date", help="取引日 (YYYY-MM-DD)")

    args = parser.parse_args()

    df = load_codes(config.codes_path)

    if args.action == "buy":
        df = buy(df, args.code, args.quantity, getattr(args, "price", None))
        if args.purpose and args.code in df["code"].values:
            df.loc[df["code"] == args.code, "purpose"] = args.purpose
    elif args.action == "prebuy":
        # pre_buy関数はquantityを固定で1として扱うため、args.quantityは不要
        # statusの決定ロジック
        prebuy_status = "監視中"  # デフォルト
        if args.watch:
            prebuy_status = "監視中"
        elif args.get:
            prebuy_status = "次回のスイングで購入"
        elif args.status:  # --watch, --get が指定されていない場合のみ --status を考慮
            prebuy_status = args.status

        df = pre_buy(
            df, args.code, 1, getattr(args, "price", None)
        )  # quantityを1に固定
        if args.purpose and args.code in df["code"].values:
            df.loc[df["code"] == args.code, "purpose"] = args.purpose
        if args.code in df["code"].values:  # statusは常に設定される
            df.loc[df["code"] == args.code, "status"] = prebuy_status
    elif args.action == "sell":
        df = sell(
            df, args.code, args.quantity, getattr(args, "profit_loss_status", None)
        )
    elif args.action == "refresh":
        df = refresh_prices(df, getattr(args, "code", None))
    elif args.action == "fixnames":
        df = fix_names(df)
    elif args.action == "csv-check":
        print(
            f"CSVファイル '{config.codes_path}' の形式チェックが完了しました。問題ありません。"
        )
        return  # CSVチェックは保存不要なのでここで終了
    elif args.action == "csv-edit":
        idx = df.index[df["code"] == args.code]
        if len(idx) > 0:
            i = idx[0]  # ここにiの定義を追加
            if args.status:
                df.at[i, "status"] = args.status
                print(f"ステータス更新: {args.code} -> {args.status}")
            if args.purpose:
                df.at[i, "purpose"] = args.purpose
                print(f"目的更新: {args.code} -> {args.purpose}")
            if not args.status and not args.purpose:
                current_status = df.at[i, "status"] if "status" in df.columns else "N/A"
                current_purpose = (
                    df.at[i, "purpose"] if "purpose" in df.columns else "N/A"
                )

                print(f"銘柄: {args.code}")
                print(f"現在のステータス: {current_status}")
                print(f"現在の目的: {current_purpose}")

                status_choices = [
                    "監視中",
                    "保有中",
                    "次回のスイングで購入",
                    "売却（利益確定）",
                    "売却（損切り）",
                    "除外",
                ]
                purpose_choices = ["present", "middle", "long", "swing"]

                print("\n変更する項目を選択してください:")
                print("1. ステータス")
                print("2. 目的")
                print("3. 両方")
                print("0. キャンセル")

                choice = input("選択: ")

                if choice == "1" or choice == "3":
                    print("\n変更先のステータスを選んでください:")
                    for j, s in enumerate(status_choices, 1):
                        print(f"{j}. {s}")
                    status_choice = input("選択: ")
                    try:
                        selected_status = status_choices[int(status_choice) - 1]
                        df.at[i, "status"] = selected_status
                        print(f"ステータス更新: {args.code} -> {selected_status}")
                    except (ValueError, IndexError):
                        print("無効な選択です。ステータスは更新されませんでした。")

                if choice == "2" or choice == "3":
                    print("\n変更先の目的を選んでください:")
                    for j, p in enumerate(purpose_choices, 1):
                        print(f"{j}. {p}")
                    purpose_choice = input("選択: ")
                    try:
                        selected_purpose = purpose_choices[int(purpose_choice) - 1]
                        df.at[i, "purpose"] = selected_purpose
                        print(f"目的更新: {args.code} -> {selected_purpose}")
                    except (ValueError, IndexError):
                        print("無効な選択です。目的は更新されませんでした。")

                if choice == "0":
                    print("変更をキャンセルしました。")
                elif choice not in ["1", "2", "3"]:
                    print("無効な選択です。")
        else:
            print(f"エラー: {args.code} はmy_stock.csvに存在しません")
    elif args.action == "add_transaction":
        add_transaction(
            args.code, args.trade_type, args.quantity, args.price, args.trade_date
        )
        return  # DBへの追加はCSV保存不要なのでここで終了

    save_codes(df, config.codes_path)


if __name__ == "__main__":
    main()
