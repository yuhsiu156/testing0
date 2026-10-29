"""Scheduled batch: snapshot fixed watchlist into data/latest.csv and history log."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from data_source import normalize_codes, fetch
from strategy import Settings, evaluate

ROOT = Path(__file__).resolve().parent
codes = normalize_codes((ROOT/'watchlist.txt').read_text(encoding='utf-8'))
rows, fails = [], []
for code in codes:
    try:
        symbol, df = fetch(code)
        item = evaluate(df, Settings()); item['股票'] = symbol
        rows.append(item)
    except Exception as e:
        fails.append(f'{code}: {e}')
if not rows:
    raise RuntimeError('所有股票下載失敗，不更新現有資料：' + ' ; '.join(fails))
folder = ROOT/'data'; folder.mkdir(exist_ok=True)
latest = pd.DataFrame(rows)
latest.to_csv(folder/'latest.csv', index=False, encoding='utf-8-sig')
history_path = folder/'history.csv'
if history_path.exists():
    history = pd.read_csv(history_path, encoding='utf-8-sig', dtype={'股票':str})
    history = pd.concat([history, latest], ignore_index=True)
    history = history.drop_duplicates(['股票','日期'], keep='last').sort_values(['日期','股票'])
else:
    history = latest
history.to_csv(history_path, index=False, encoding='utf-8-sig')
print('更新時間(台北):', datetime.now(ZoneInfo('Asia/Taipei')).isoformat(), '成功:', len(rows), '失敗:', fails)
