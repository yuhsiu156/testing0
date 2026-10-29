import pandas as pd
import numpy as np
from strategy import Settings, evaluate
from data_source import normalize_codes, candidates

def test_codes():
    assert normalize_codes('2330, 6488.TWO 2330') == ['2330','6488.TWO']
    assert candidates('2330') == ['2330.TW','2330.TWO']

def test_breakout_reference_excludes_today():
    idx = pd.bdate_range('2025-01-01', periods=110)
    df = pd.DataFrame({'Open':100.,'High':102.,'Low':95.,'Close':100.,'Volume':1000.}, index=idx)
    df.iloc[-1, df.columns.get_loc('High')] = 110.
    df.iloc[-1, df.columns.get_loc('Close')] = 104.
    df.iloc[-1, df.columns.get_loc('Volume')] = 2000.
    res = evaluate(df, Settings())
    assert res['突破價'] == 102.0
    assert res['帶量突破'] if '帶量突破' in res else res['條件_帶量突破']
    assert res['距突破價%'] > 0
