# Phase 4: 運用監視機能の実装ログ

本ドキュメントは、デプロイ計画フェーズ4「運用監視」において実装された機能、特にWeb UIからの手動操作、ルール変更管理、およびシグナル判定トリガーに関する実装詳細を記録したものです。

## 1. ルール変更管理の強化

運用中にトレーディングルールを変更する際、その「理由」を明確に記録し、後から分析できるようにしました。

### 1-1. スキーマ定義 (`python/web/schemas.py`)

`ChangeReason` Enumを定義し、`TradingRules` モデルに `change_reason` と `change_note` フィールドを追加しました。

```python
class ChangeReason(str, Enum):
    PERFORMANCE = "Performance Optimization"
    RISK = "Risk Mitigation"
    MARKET = "Market Regime Change"
    FIX = "Logic Correction"
    REGULAR = "Regular Update"
    TEST = "Testing"
    OTHER = "Other"

class TradingRules(BaseModel):
    # ... 既存フィールド ...
    change_reason: ChangeReason = Field(
        default=ChangeReason.REGULAR,
        description="Reason for this rule change"
    )
    change_note: Optional[str] = Field(
        default="",
        description="Optional detailed note about the change"
    )
```

### 1-2. Web UI 実装 (`python/web/templates/index.html`)

設定画面にプルダウンメニューを追加し、選択した理由に応じて説明文を表示するロジックをVue.jsで実装しました。

```html
<!-- HTML部分 -->
<select v-model="rules.change_reason">
    <option value="Performance Optimization">パフォーマンス最適化</option>
    <!-- ... -->
</select>
<div v-if="rules.change_reason === 'Other'">
    <input v-model="rules.change_note" placeholder="詳細を入力...">
</div>
```

## 2. 手動アクションとレートリミット

Web UIから「株価データの更新」や「シグナル判定」を手動でトリガーできる機能を追加しました。特に株価更新は負荷が高いため、1時間のクールダウン（レートリミット）を設けています。

### 2-1. API エンドポイント (`python/web/routes/actions.py`)

FastAPIの `BackgroundTasks` を利用して非同期に処理を実行し、インメモリで簡易的な状態管理を行っています。

```python
# 状態管理用クラス
class ActionState:
    last_update_time: Optional[datetime] = None
    is_updating: bool = False
    is_analyzing: bool = False

_state = ActionState()
_UPDATE_COOLDOWN = timedelta(hours=1)

@router.post("/update-market-data")
async def trigger_market_update(background_tasks: BackgroundTasks):
    now = datetime.now()
    
    # 実行中チェック
    if _state.is_updating:
        raise HTTPException(status_code=409, detail="Update already in progress")

    # クールダウンチェック
    if _state.last_update_time:
        elapsed = now - _state.last_update_time
        if elapsed < _UPDATE_COOLDOWN:
            raise HTTPException(status_code=429, detail="Update limit reached.")

    _state.is_updating = True
    _state.last_update_time = now
    background_tasks.add_task(_run_market_update)
    return {"status": "accepted"}
```

### 2-2. UI連携 (`python/web/templates/index.html`)

ヘッダーにアクションボタンを配置し、ステータスAPI (`/api/actions/status`) を定期的にポーリングしてボタンの有効/無効を切り替えています。

## 3. ルール見直し基準の策定

システムが不調な場合に、ルール変更を検討するための定量的な基準を策定しました。これらは自動変更ではなく、人間が判断するためのアラート基準として機能します。

| 指標 | 基準値 | 理由 |
| :--- | :--- | :--- |
| **Profit Factor** | **1.2 未満** (直近3ヶ月) | 損益分岐点+αを下回る場合、ロジックの優位性が失われている可能性。 |
| **Max Drawdown** | **15% 超過** | 復帰困難な水準(20%~)に達する前に警告。 |
| **勝率** | **35% 未満** | トレンドフォロー型でも30%を切ると連敗確率が許容範囲を超えるため。 |
| **連続敗戦数** | **6連敗 以上** | 勝率40%想定での発生確率5%未満。相場環境との不一致を示唆。 |

## 4. 今後の課題

- `actions.py` 内の `_run_market_update` 等の中身は現在モック（`time.sleep`）になっているため、実際の `python.watch` モジュール等の呼び出しを実装する必要があります。