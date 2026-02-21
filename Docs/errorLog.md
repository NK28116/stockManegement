## log

```log
INFO:     Will watch for changes in these directories: ['/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement']
INFO:     Uvicorn running on http://127.0.0.1:8888 (Press CTRL+C to quit)
INFO:     Started reloader process [45948] using StatReload
[INFO] GCSClient initialized in LOCAL mode.
INFO:     Started server process [45951]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     127.0.0.1:53513 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:53513 - "GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1" 404 Not Found
INFO:python.web.routes.charts:Loaded 10 entries from latest_indicators.json
DEBUG: Found 10 companies
INFO:     127.0.0.1:53511 - "GET /api/charts/list HTTP/1.1" 200 OK
INFO:     127.0.0.1:53511 - "GET /api/charts/image/plots/7803.T_BUSHIROAD%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/actions/status HTTP/1.1" 200 OK
2026-02-21 23:53 - ERROR - 最新シグナル取得エラー: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
psycopg2.errors.UndefinedTable: relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement/python/web/api/signals.py", line 128, in get_latest_signals
    rows = conn.execute(query).fetchall()
           ^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1418, in execute
    return meth(
           ^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 515, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1640, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2355, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:     127.0.0.1:53543 - "GET /api/signals/latest HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:53549 - "GET /api/charts/image/chartImg/7803_T_BUSHIROAD%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53511 - "GET /api/charts/image/chartImg/9434_T_SOFTBANK%20CORP..png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/charts/image/plots/5253.T_COVER%20CORPORATION_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53543 - "GET /api/charts/image/chartImg/5253_T_COVER%20CORPORATION.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53549 - "GET /api/charts/image/plots/9434.T_SOFTBANK%20CORP._indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53517 - "GET /api/rules/active HTTP/1.1" 200 OK
INFO:     127.0.0.1:53540 - "GET /api/rules/history HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/charts/image/plots/9104.T_MITSUI%20O.S.K.%20LINES%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53543 - "GET /api/charts/image/chartImg/9104_T_MITSUI%20O.S.K.%20LINES%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53511 - "GET /api/charts/image/plots/6503.T_MITSUBISHI%20ELECTRIC%20CORP_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53549 - "GET /api/charts/image/chartImg/6503_T_MITSUBISHI%20ELECTRIC%20CORP.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53517 - "GET /api/charts/image/plots/7203.T_TOYOTA%20MOTOR%20CORP_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53540 - "GET /api/charts/image/chartImg/7203_T_TOYOTA%20MOTOR%20CORP.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53543 - "GET /api/charts/image/plots/9312.T_KEIHIN%20CO%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53511 - "GET /api/charts/image/chartImg/9312_T_KEIHIN%20CO%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53549 - "GET /api/charts/image/plots/9193.T_TOKYO%20KISEN%20CO%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53517 - "GET /api/charts/image/chartImg/9193_T_TOKYO%20KISEN%20CO%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53540 - "GET /api/charts/image/plots/5020.T_ENEOS%20HOLDINGS%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53543 - "GET /api/charts/image/chartImg/5020_T_ENEOS%20HOLDINGS%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53549 - "GET /api/charts/image/plots/9432.T_NTT%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/rules/history/17 HTTP/1.1" 200 OK
INFO:     127.0.0.1:53517 - "GET /api/charts/image/chartImg/9432_T_NTT%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/rules/history/16 HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/rules/history/15 HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/rules/history/14 HTTP/1.1" 200 OK
INFO:     127.0.0.1:53541 - "GET /api/rules/history/13 HTTP/1.1" 200 OK
INFO:     127.0.0.1:53702 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:     127.0.0.1:53819 - "POST /api/signals/analyze HTTP/1.1" 202 Accepted
2026-02-21 23:54 - INFO - 週足スイング分析 バックグラウンドタスク 開始
INFO:analyze:週足スイングトレード分析 開始
INFO:analyze:分析対象銘柄数: 9
INFO:analyze:データ取得成功: 9434.T (取得行数=105)
INFO:analyze:[9434.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders', 'flag']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9434.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 'stop_loss': 219.87706796323693, 'take_profit': 190.24586407352615, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 9, 819448)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9434.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9434.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 'stop_loss': 219.87706796323693, 'take_profit': 190.24586407352615, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 9, 819448)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 7803.T (取得行数=105)
INFO:analyze:[7803.T] trend=SHORT score=7/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7803.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 7, 'detected_patterns': '["volume_surge"]', 'stop_loss': 301.23162227822854, 'take_profit': 195.53675544354286, 'rationale': 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 11, 8226)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (7803.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7803.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 7, 'detected_patterns': '["volume_surge"]', 'stop_loss': 301.23162227822854, 'take_profit': 195.53675544354286, 'rationale': 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 11, 8226)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 7203.T (取得行数=105)
INFO:analyze:[7203.T] trend=LONG score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7203.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 3331.5222341551075, 'take_profit': 4241.955531689785, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 12, 184744)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (7203.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7203.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 3331.5222341551075, 'take_profit': 4241.955531689785, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 12, 184744)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:     127.0.0.1:53855 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:analyze:データ取得成功: 6503.T (取得行数=105)
INFO:analyze:[6503.T] trend=LONG score=5/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '6503.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 5, 'detected_patterns': '["volume_surge"]', 'stop_loss': 5377.865014038305, 'take_profit': 6794.269971923389, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 13, 333409)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (6503.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '6503.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 5, 'detected_patterns': '["volume_surge"]', 'stop_loss': 5377.865014038305, 'take_profit': 6794.269971923389, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 13, 333409)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9432.T (取得行数=105)
INFO:analyze:[9432.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9432.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 157.63223549175328, 'take_profit': 137.73552901649344, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 14, 558108)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9432.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9432.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 157.63223549175328, 'take_profit': 137.73552901649344, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 14, 558108)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9312.T (取得行数=105)
INFO:analyze:[9312.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9312.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 3045.8870199456155, 'take_profit': 3733.225960108769, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 15, 724362)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9312.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9312.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 3045.8870199456155, 'take_profit': 3733.225960108769, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 15, 724362)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 5020.T (取得行数=105)
INFO:analyze:[5020.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5020.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 1359.2715622032802, 'take_profit': 1649.4568755934397, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 16, 891986)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (5020.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5020.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 1359.2715622032802, 'take_profit': 1649.4568755934397, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 16, 891986)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9193.T (取得行数=105)
INFO:analyze:[9193.T] trend=LONG score=9/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9193.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 9, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 1177.178767402324, 'take_profit': 1425.6424651953523, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 18, 58630)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9193.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9193.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 9, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 1177.178767402324, 'take_profit': 1425.6424651953523, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 18, 58630)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 5253.T (取得行数=105)
INFO:analyze:[5253.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5253.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 1939.4994884217786, 'take_profit': 1191.001023156443, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 19, 170339)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (5253.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5253.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 1939.4994884217786, 'take_profit': 1191.001023156443, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 19, 170339)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:週足スイングトレード分析 完了
2026-02-21 23:54 - INFO - 週足スイング分析 バックグラウンドタスク 完了
INFO:     127.0.0.1:53897 - "GET /api/signals/status HTTP/1.1" 200 OK
2026-02-21 23:54 - ERROR - 最新シグナル取得エラー: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
psycopg2.errors.UndefinedTable: relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement/python/web/api/signals.py", line 128, in get_latest_signals
    rows = conn.execute(query).fetchall()
           ^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1418, in execute
    return meth(
           ^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 515, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1640, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2355, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:     127.0.0.1:53897 - "GET /api/signals/latest HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:54007 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:     127.0.0.1:54063 - "POST /api/signals/analyze HTTP/1.1" 202 Accepted
2026-02-21 23:54 - INFO - 週足スイング分析 バックグラウンドタスク 開始
INFO:analyze:週足スイングトレード分析 開始
INFO:analyze:分析対象銘柄数: 9
INFO:analyze:データ取得成功: 9434.T (取得行数=105)
INFO:analyze:[9434.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders', 'flag']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9434.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 'stop_loss': 219.87706797453222, 'take_profit': 190.24586405093555, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 54, 218501)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9434.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9434.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 'stop_loss': 219.87706797453222, 'take_profit': 190.24586405093555, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 54, 218501)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 7803.T (取得行数=105)
INFO:analyze:[7803.T] trend=SHORT score=7/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7803.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 7, 'detected_patterns': '["volume_surge"]', 'stop_loss': 301.23162227867977, 'take_profit': 195.5367554426404, 'rationale': 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 55, 341008)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (7803.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7803.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 7, 'detected_patterns': '["volume_surge"]', 'stop_loss': 301.23162227867977, 'take_profit': 195.5367554426404, 'rationale': 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 55, 341008)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 7203.T (取得行数=105)
INFO:analyze:[7203.T] trend=LONG score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7203.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 3331.522233121389, 'take_profit': 4241.955533757222, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 56, 512809)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (7203.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '7203.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 3331.522233121389, 'take_profit': 4241.955533757222, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 56, 512809)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 6503.T (取得行数=105)
INFO:analyze:[6503.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '6503.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 5377.865016407247, 'take_profit': 6794.269967185507, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 57, 683091)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (6503.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '6503.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 5377.865016407247, 'take_profit': 6794.269967185507, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 57, 683091)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9432.T (取得行数=105)
INFO:analyze:[9432.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9432.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 157.6322354963276, 'take_profit': 137.73552900734478, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 58, 849858)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9432.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9432.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 157.6322354963276, 'take_profit': 137.73552900734478, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 54, 58, 849858)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9312.T (取得行数=105)
INFO:analyze:[9312.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9312.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 3045.8870199465464, 'take_profit': 3733.225960106907, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 1, 494424)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9312.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9312.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 3045.8870199465464, 'take_profit': 3733.225960106907, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 1, 494424)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 5020.T (取得行数=105)
INFO:analyze:[5020.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5020.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 1359.2715622764842, 'take_profit': 1649.4568754470315, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 2, 628070)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (5020.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5020.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'NONE', 'score': 6, 'detected_patterns': '["volume_surge"]', 'stop_loss': 1359.2715622764842, 'take_profit': 1649.4568754470315, 'rationale': 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 2, 628070)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 9193.T (取得行数=105)
INFO:analyze:[9193.T] trend=LONG score=9/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9193.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 9, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 1177.178767402324, 'take_profit': 1425.6424651953523, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 3, 777613)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (9193.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '9193.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'LONG', 'score': 9, 'detected_patterns': '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 'stop_loss': 1177.178767402324, 'take_profit': 1425.6424651953523, 'rationale': 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 3, 777613)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:データ取得成功: 5253.T (取得行数=105)
INFO:analyze:[5253.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5253.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 1939.4994884217786, 'take_profit': 1191.001023156443, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 4, 893048)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
ERROR:analyze:シグナル保存エラー (5253.T): (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 1: INSERT INTO signals (symbol, analysis_date, signal_type, sco...
                    ^

[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (%(symbol)s, %(analysis_date)s, %(signal_type)s, %(score)s, %(detected_patterns)s, %(stop_loss)s, %(take_profit)s, %(rationale)s, %(created_at)s) RETURNING signals.id]
[parameters: {'symbol': '5253.T', 'analysis_date': datetime.date(2026, 2, 21), 'signal_type': 'SHORT', 'score': 10, 'detected_patterns': '["volume_surge", "double_bottom"]', 'stop_loss': 1939.4994884217786, 'take_profit': 1191.001023156443, 'rationale': 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', 'created_at': datetime.datetime(2026, 2, 21, 23, 55, 4, 893048)}]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:analyze:週足スイングトレード分析 完了
2026-02-21 23:55 - INFO - 週足スイング分析 バックグラウンドタスク 完了
INFO:     127.0.0.1:54145 - "GET /api/signals/status HTTP/1.1" 200 OK
2026-02-21 23:55 - ERROR - 最新シグナル取得エラー: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
psycopg2.errors.UndefinedTable: relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^


The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement/python/web/api/signals.py", line 128, in get_latest_signals
    rows = conn.execute(query).fetchall()
           ^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1418, in execute
    return meth(
           ^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 515, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1640, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2355, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "signals" does not exist
LINE 6:             FROM signals t1
                         ^

[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/f405)
INFO:     127.0.0.1:54145 - "GET /api/signals/latest HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:54145 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:     127.0.0.1:54326 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:     127.0.0.1:54483 - "GET /api/actions/status HTTP/1.1" 200 OK

```

## Log2

 ```Log
 [INFO] GCSClient initialized in LOCAL mode.
INFO:     Started server process [48435]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8888 (Press CTRL+C to quit)
INFO:     127.0.0.1:59014 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1" 404 Not Found
INFO:python.web.routes.charts:Loaded 10 entries from latest_indicators.json
DEBUG: Found 10 companies
INFO:     127.0.0.1:59014 - "GET /api/charts/list HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /api/charts/image/plots/7803.T_BUSHIROAD%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59028 - "GET /api/actions/status HTTP/1.1" 200 OK
2026-02-22 00:09 - ERROR - 最新シグナル取得エラー: (sqlite3.OperationalError) no such table: signals
[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlite3.OperationalError: no such table: signals

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement/python/web/api/signals.py", line 128, in get_latest_signals
    rows = conn.execute(query).fetchall()
           ^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1418, in execute
    return meth(
           ^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 515, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1640, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2355, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: signals
[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:     127.0.0.1:59029 - "GET /api/signals/latest HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:59031 - "GET /api/charts/image/chartImg/7803_T_BUSHIROAD%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /api/charts/image/plots/9434.T_SOFTBANK%20CORP._indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59028 - "GET /api/charts/image/chartImg/9434_T_SOFTBANK%20CORP..png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59029 - "GET /api/charts/image/chartImg/5253_T_COVER%20CORPORATION.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/charts/image/plots/5253.T_COVER%20CORPORATION_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /api/charts/image/plots/9104.T_MITSUI%20O.S.K.%20LINES%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59016 - "GET /api/rules/active HTTP/1.1" 200 OK
INFO:     127.0.0.1:59027 - "GET /api/rules/history HTTP/1.1" 200 OK
INFO:     127.0.0.1:59028 - "GET /api/charts/image/chartImg/9104_T_MITSUI%20O.S.K.%20LINES%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59029 - "GET /api/charts/image/plots/6503.T_MITSUBISHI%20ELECTRIC%20CORP_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/charts/image/chartImg/6503_T_MITSUBISHI%20ELECTRIC%20CORP.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /api/charts/image/plots/7203.T_TOYOTA%20MOTOR%20CORP_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59016 - "GET /api/charts/image/chartImg/7203_T_TOYOTA%20MOTOR%20CORP.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59027 - "GET /api/charts/image/plots/9312.T_KEIHIN%20CO%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59028 - "GET /api/charts/image/chartImg/9312_T_KEIHIN%20CO%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59029 - "GET /api/charts/image/plots/9193.T_TOKYO%20KISEN%20CO%20LTD_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59014 - "GET /api/charts/image/chartImg/9193_T_TOKYO%20KISEN%20CO%20LTD.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59016 - "GET /api/charts/image/plots/5020.T_ENEOS%20HOLDINGS%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59027 - "GET /api/charts/image/chartImg/5020_T_ENEOS%20HOLDINGS%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59028 - "GET /api/charts/image/plots/9432.T_NTT%20INC_indicators.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59029 - "GET /api/charts/image/chartImg/9432_T_NTT%20INC.png HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/rules/history/17 HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/rules/history/16 HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/rules/history/15 HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/rules/history/14 HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "GET /api/rules/history/13 HTTP/1.1" 200 OK
INFO:     127.0.0.1:59031 - "POST /api/signals/analyze HTTP/1.1" 202 Accepted
2026-02-22 00:09 - INFO - 週足スイング分析 バックグラウンドタスク 開始
INFO:analyze:週足スイングトレード分析 開始
INFO:analyze:分析対象銘柄数: 9
INFO:     127.0.0.1:59031 - "GET /api/actions/status HTTP/1.1" 200 OK
INFO:analyze:データ取得成功: 9434.T (取得行数=105)
INFO:analyze:[9434.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders', 'flag']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9434.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 219.87706796323693, 190.24586407352615, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', '2026-02-22 00:09:43.721482')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (9434.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9434.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom", "inverse_head_and_shoulders", "flag"]', 219.87706796323693, 190.24586407352615, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders,flag): +3 / 出来高増加: +2 / RSI適正(38.3): +1 / RR良好(2.0): +1', '2026-02-22 00:09:43.721482')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 7803.T (取得行数=105)
INFO:analyze:[7803.T] trend=SHORT score=7/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('7803.T', '2026-02-22', 'NONE', 7, '["volume_surge"]', 301.23162227822854, 195.53675544354286, 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', '2026-02-22 00:09:44.869368')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (7803.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('7803.T', '2026-02-22', 'NONE', 7, '["volume_surge"]', 301.23162227822854, 195.53675544354286, 'トレンド一致(SHORT): +3 / 出来高増加: +2 / RSI適正(43.4): +1 / RR良好(2.0): +1', '2026-02-22 00:09:44.869368')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 7203.T (取得行数=105)
INFO:analyze:[7203.T] trend=LONG score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('7203.T', '2026-02-22', 'LONG', 10, '["volume_surge", "double_bottom"]', 3331.522233484735, 4241.95553303053, 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', '2026-02-22 00:09:46.040597')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (7203.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('7203.T', '2026-02-22', 'LONG', 10, '["volume_surge", "double_bottom"]', 3331.522233484735, 4241.95553303053, 'トレンド一致(LONG): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(64.4): +1 / RR良好(2.0): +1', '2026-02-22 00:09:46.040597')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 6503.T (取得行数=105)
INFO:analyze:[6503.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('6503.T', '2026-02-22', 'NONE', 6, '["volume_surge"]', 5377.865016450014, 6794.269967099973, 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:47.222653')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (6503.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('6503.T', '2026-02-22', 'NONE', 6, '["volume_surge"]', 5377.865016450014, 6794.269967099973, 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:47.222653')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 9432.T (取得行数=105)
INFO:analyze:[9432.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9432.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 157.63223549175328, 137.73552901649344, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', '2026-02-22 00:09:48.408739')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (9432.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9432.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 157.63223549175328, 137.73552901649344, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RSI適正(49.6): +1 / RR良好(2.0): +1', '2026-02-22 00:09:48.408739')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 9312.T (取得行数=105)
INFO:analyze:[9312.T] trend=LONG score=6/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9312.T', '2026-02-22', 'NONE', 6, '["volume_surge"]', 3045.8870199465464, 3733.225960106907, 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:49.588708')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (9312.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9312.T', '2026-02-22', 'NONE', 6, '["volume_surge"]', 3045.8870199465464, 3733.225960106907, 'トレンド一致(LONG): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:49.588708')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 5020.T (取得行数=105)
INFO:analyze:[5020.T] trend=LONG score=5/8 [閾値未達(閾値=8)] patterns=['volume_surge']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('5020.T', '2026-02-22', 'NONE', 5, '["volume_surge"]', 1359.2715622938438, 1649.4568754123122, 'トレンド一致(LONG): +3 / 出来高増加: +2', '2026-02-22 00:09:50.746395')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (5020.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('5020.T', '2026-02-22', 'NONE', 5, '["volume_surge"]', 1359.2715622938438, 1649.4568754123122, 'トレンド一致(LONG): +3 / 出来高増加: +2', '2026-02-22 00:09:50.746395')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 9193.T (取得行数=105)
INFO:analyze:[9193.T] trend=LONG score=9/8 [有効シグナル] patterns=['volume_surge', 'double_bottom', 'inverse_head_and_shoulders']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9193.T', '2026-02-22', 'LONG', 9, '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 1177.178767402324, 1425.6424651953523, 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:51.977284')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (9193.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('9193.T', '2026-02-22', 'LONG', 9, '["volume_surge", "double_bottom", "inverse_head_and_shoulders"]', 1177.178767402324, 1425.6424651953523, 'トレンド一致(LONG): +3 / パターン検出(double_bottom,inverse_head_and_shoulders): +3 / 出来高増加: +2 / RR良好(2.0): +1', '2026-02-22 00:09:51.977284')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:データ取得成功: 5253.T (取得行数=105)
INFO:analyze:[5253.T] trend=SHORT score=10/8 [有効シグナル] patterns=['volume_surge', 'double_bottom']
ERROR:python.db.database:Database session error: (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('5253.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom"]', 1939.4994884217786, 1191.001023156443, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', '2026-02-22 00:09:53.129064')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
ERROR:analyze:シグナル保存エラー (5253.T): (sqlite3.OperationalError) no such table: signals
[SQL: INSERT INTO signals (symbol, analysis_date, signal_type, score, detected_patterns, stop_loss, take_profit, rationale, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)]
[parameters: ('5253.T', '2026-02-22', 'SHORT', 10, '["volume_surge", "double_bottom"]', 1939.4994884217786, 1191.001023156443, 'トレンド一致(SHORT): +3 / パターン検出(double_bottom): +3 / 出来高増加: +2 / RSI適正(50.6): +1 / RR良好(2.0): +1', '2026-02-22 00:09:53.129064')]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:analyze:週足スイングトレード分析 完了
2026-02-22 00:09 - INFO - 週足スイング分析 バックグラウンドタスク 完了
INFO:     127.0.0.1:59131 - "GET /api/signals/status HTTP/1.1" 200 OK
2026-02-22 00:09 - ERROR - 最新シグナル取得エラー: (sqlite3.OperationalError) no such table: signals
[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlite3.OperationalError: no such table: signals

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/niwa_kazuhiro/Documents/PrivateDevelop/stockManegement/python/web/api/signals.py", line 128, in get_latest_signals
    rows = conn.execute(query).fetchall()
           ^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1418, in execute
    return meth(
           ^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/sql/elements.py", line 515, in _execute_on_connection
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1640, in _execute_clauseelement
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1846, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1986, in _exec_single_context
    self._handle_dbapi_exception(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 2355, in _handle_dbapi_exception
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/base.py", line 1967, in _exec_single_context
    self.dialect.do_execute(
  File "/Users/niwa_kazuhiro/anaconda3/lib/python3.12/site-packages/sqlalchemy/engine/default.py", line 941, in do_execute
    cursor.execute(statement, parameters)
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: signals
[SQL: 
            SELECT
                t1.id, t1.symbol, t1.analysis_date, t1.signal_type, t1.score,
                t1.detected_patterns, t1.stop_loss, t1.take_profit, t1.rationale, t1.created_at,
                CASE WHEN p.code IS NOT NULL THEN TRUE ELSE FALSE END AS is_held
            FROM signals t1
            JOIN (
                SELECT symbol, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol
            ) t2 ON t1.symbol = t2.symbol AND t1.created_at = t2.max_created_at
            LEFT JOIN (
                SELECT DISTINCT code
                FROM portfolio
                WHERE status NOT IN ('SOLD_PROFIT', 'SOLD_LOSS', '売却（利益確定）', '売却（損切り）')
            ) p ON t1.symbol = p.code
            ORDER BY t1.signal_type DESC, t1.score DESC
            ]
(Background on this error at: https://sqlalche.me/e/20/e3q8)
INFO:     127.0.0.1:59131 - "GET /api/signals/latest HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:59194 - "GET /api/actions/status HTTP/1.1" 200 OK

 ```