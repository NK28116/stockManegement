"""ダッシュボードの実ブラウザ回帰テスト (PRIDEV-484 / PRIDEV-526 / PRIDEV-527)

本物の uvicorn でアプリを起動し、Chromium (Playwright) で画面を描画して検証する。
Tailwind CSS / Vue は python/web/static/ から自前配信しているため、
CDN に到達できないオフライン環境でも実際のレイアウトを評価できる。

バックエンドのデータ取得 (/api/charts/list など) は Playwright でスタブし、
DB やネットワークに依存しない。/api/choices だけは実装の応答を使い、
バックエンド定義 (STATUS_CHOICES) と画面の並び順が一致することを確かめる。

Playwright またはブラウザが利用できない環境ではスキップする。
ブラウザの場所が既定と異なる場合は PLAYWRIGHT_CHROMIUM_EXECUTABLE で指定する。
"""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

playwright_api = pytest.importorskip("playwright.sync_api")

from python.trading.stock_status import STATUS_CHOICES  # noqa: E402

VIEWPORTS = {
    "mobile-small": 320,
    "mobile": 375,
    "tablet": 768,
    "laptop": 1024,
    "desktop": 1440,
}

# 表示順を確認するため、定義順と逆順・未知ステータスを混ぜて返す
CHART_STATUSES = [choice.key for choice in reversed(STATUS_CHOICES)] + ["UNKNOWN_STATUS"]


def _chart(index: int, status: str) -> dict:
    return {
        "code": f"{1000 + index}",
        "name": f"テスト銘柄{index}",
        "status": status,
        "purpose": "swing",
        "current_price": 1234.5,
        "profit_loss": 1000,
        "profit_loss_percent": 1.2,
        "purchase_price": 1200,
        "quantity": 100,
        "purchase_date": "2026-01-01",
        "last_updated": "2026-08-25 12:00",
        "plots": None,
        "chartImg": None,
    }


CHARTS = [_chart(index, status) for index, status in enumerate(CHART_STATUSES)]

# mounted() が呼ぶ API のスタブ応答
API_STUBS = {
    "/api/rules/active": {"version": 1, "change_reason": "test"},
    "/api/rules/default": {},
    "/api/rules/history": [],
    "/api/actions/status": {"can_update": True, "is_updating": False, "is_analyzing": False},
    "/api/signals/latest": {"results": []},
    "/api/startup/status": {"ready": True},
}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    import uvicorn

    from python.web import auth

    # 開発環境として認証を無効化した状態で画面そのものを検証する
    saved = {name: os.environ.get(name) for name in ("APP_ENV", "APP_PASSWORD_HASH")}
    os.environ["APP_ENV"] = "test"
    os.environ.pop("APP_PASSWORD_HASH", None)
    auth.reset_auth_settings_cache()

    from python.web.app import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 15
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "テスト用サーバーが起動しませんでした"

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    auth.reset_auth_settings_cache()


@pytest.fixture(scope="module")
def browser():
    with playwright_api.sync_playwright() as playwright:
        try:
            launched = playwright.chromium.launch()
        except Exception as default_error:
            executable = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
            if not executable:
                pytest.skip(f"Chromium を起動できません: {default_error}")
            launched = playwright.chromium.launch(executable_path=executable)
        yield launched
        launched.close()


def _open_dashboard(browser, base_url, width, *, choices_delay_ms=0, charts=CHARTS):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    page_errors = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))
    page.on(
        "console",
        lambda message: page_errors.append(message.text) if message.type == "error" else None,
    )

    def handle_api(route):
        path = route.request.url.replace(base_url, "").split("?")[0]
        if path == "/api/charts/list":
            route.fulfill(status=200, content_type="application/json", body=json.dumps(charts))
        elif path == "/api/choices":
            # 実装の応答を使う。遅延させて「チャートが先に返る」競合を再現する
            response = route.fetch()
            if choices_delay_ms:
                page.wait_for_timeout(choices_delay_ms)
            route.fulfill(response=response)
        elif path in API_STUBS:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(API_STUBS[path]))
        else:
            route.fulfill(status=404, content_type="application/json", body="{}")

    page.route("**/api/**", handle_api)
    page.goto(f"{base_url}/", wait_until="load")
    page.wait_for_selector(".table-scroll table tbody tr", timeout=10000)
    return context, page, page_errors


def _row_statuses(page):
    return page.eval_on_selector_all(
        ".table-scroll tbody tr",
        "rows => rows.map(row => row.querySelector('.text-sm.text-gray-500').textContent.trim())",
    )


def _expected_codes():
    order = {choice.key: index for index, choice in enumerate(STATUS_CHOICES)}
    ordered = sorted(CHARTS, key=lambda chart: order.get(chart["status"], len(order)))
    return [chart["code"] for chart in ordered]


# --- PRIDEV-527: Vue テンプレートがマウントでき、表がデータあり時に表示される -----
def test_dashboard_mounts_without_errors(browser, base_url):
    context, page, page_errors = _open_dashboard(browser, base_url, 1440)
    try:
        assert page_errors == []
        assert page.locator(".table-scroll tbody tr").count() == len(CHARTS)
        # 状態表示 (loading / error / empty) は表と同時に出ない
        assert page.get_by_text("Loading charts...").count() == 0
        assert page.get_by_text("No charts found.").count() == 0
    finally:
        context.close()


def test_empty_state_hides_table_and_keeps_purchase_form(browser, base_url):
    context = browser.new_context(viewport={"width": 1024, "height": 900})
    page = context.new_page()
    try:
        page.route(
            "**/api/**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body="[]" if "/api/charts/list" in route.request.url else "{}",
            ),
        )
        page.goto(f"{base_url}/", wait_until="load")
        page.wait_for_selector("text=No charts found.")

        assert page.locator(".table-scroll table").count() == 0
        assert page.get_by_text("銘柄の登録").is_visible()
    finally:
        context.close()


# --- PRIDEV-484 / 527: 代表幅で横 overflow が無く、主要要素が切れない -------------
@pytest.mark.parametrize("name,width", sorted(VIEWPORTS.items(), key=lambda item: item[1]))
def test_no_page_level_horizontal_overflow(browser, base_url, name, width):
    context, page, _ = _open_dashboard(browser, base_url, width)
    try:
        metrics = page.evaluate(
            """() => ({
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                bodyOverflowX: getComputedStyle(document.body).overflowX,
            })"""
        )
        assert metrics["scrollWidth"] <= metrics["clientWidth"], f"{name}({width}px): {metrics}"
        # はみ出しを overflow:hidden で隠していないこと (原因側で抑える)
        assert metrics["bodyOverflowX"] != "hidden"
    finally:
        context.close()


@pytest.mark.parametrize("name,width", sorted(VIEWPORTS.items(), key=lambda item: item[1]))
def test_purchase_form_controls_are_fully_visible(browser, base_url, name, width):
    context, page, _ = _open_dashboard(browser, base_url, width)
    try:
        boxes = page.eval_on_selector_all(
            ".form-control",
            """elements => elements.map(element => {
                const rect = element.getBoundingClientRect()
                return {tag: element.tagName, left: rect.left, right: rect.right,
                        top: rect.top, height: rect.height}
            })""",
        )
        assert len(boxes) == 6  # 区分 / 銘柄 / 株数 / 概算 / 目的別 / ボタン
        for box in boxes:
            assert box["left"] >= 0 and box["right"] <= width, f"{name}({width}px) で切れている: {box}"

        heights = {round(box["height"]) for box in boxes}
        assert len(heights) == 1, f"input / select / button の高さが揃っていない: {boxes}"

        if width >= 640:
            # 通常幅では横並びになり、input と select の基準位置 (top) が揃う
            fields = [box for box in boxes if box["tag"] in ("INPUT", "SELECT")]
            tops = {round(box["top"]) for box in fields}
            if len(tops) > 1:
                # 折り返した場合も、同じ行の要素同士は top が揃っていること
                rows = {}
                for box in fields:
                    rows.setdefault(round(box["top"]), []).append(box)
                assert all(len({round(b["top"]) for b in row}) == 1 for row in rows.values())
            else:
                assert len(tops) == 1
    finally:
        context.close()


@pytest.mark.parametrize("width", [320, 375])
def test_table_scrolls_inside_container_on_small_screens(browser, base_url, width):
    context, page, _ = _open_dashboard(browser, base_url, width)
    try:
        container = page.evaluate(
            """() => {
                const element = document.querySelector('.table-scroll')
                const rect = element.getBoundingClientRect()
                return {right: rect.right, overflowX: getComputedStyle(element).overflowX}
            }"""
        )
        assert container["right"] <= width
        assert container["overflowX"] == "auto"
    finally:
        context.close()


# --- PRIDEV-526: STATUS_CHOICES の定義順で並び、応答順の競合でも崩れない -----------
def test_rows_follow_status_choices_order(browser, base_url):
    context, page, _ = _open_dashboard(browser, base_url, 1440)
    try:
        page.wait_for_function(
            "expected => [...document.querySelectorAll('.table-scroll tbody tr')]"
            ".map(row => row.querySelector('.text-sm.text-gray-500').textContent.trim())"
            ".join(',') === expected",
            arg=",".join(_expected_codes()),
            timeout=5000,
        )
        assert _row_statuses(page) == _expected_codes()
    finally:
        context.close()


def test_order_is_correct_when_charts_respond_before_choices(browser, base_url):
    context, page, _ = _open_dashboard(browser, base_url, 1440, choices_delay_ms=800)
    try:
        page.wait_for_function(
            "expected => [...document.querySelectorAll('.table-scroll tbody tr')]"
            ".map(row => row.querySelector('.text-sm.text-gray-500').textContent.trim())"
            ".join(',') === expected",
            arg=",".join(_expected_codes()),
            timeout=5000,
        )
        rows = _row_statuses(page)
        assert rows == _expected_codes()
        # 未知のステータスは既知ステータスの後ろ
        assert rows[-1] == CHARTS[-1]["code"]
    finally:
        context.close()


# --- ダッシュボード ⇔ System Monitor の導線 -----------------------------------
@pytest.mark.parametrize("width", [375, 1440])
def test_dashboard_and_system_monitor_link_to_each_other(browser, base_url, width):
    context, page, _ = _open_dashboard(browser, base_url, width)
    try:
        assert page.get_by_role("button", name="ログアウト").is_visible()

        page.click("a[data-nav=system-monitor]")
        page.wait_for_url(f"{base_url}/system-monitor")
        assert page.get_by_role("heading", name="System Monitor").is_visible()

        page.click("a[data-nav=dashboard]")
        page.wait_for_url(f"{base_url}/")
        page.wait_for_selector(".table-scroll table tbody tr", timeout=10000)
    finally:
        context.close()
