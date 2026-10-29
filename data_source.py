"""Yahoo Finance daily bars, adjusted OHLC; not exchange-licensed realtime feed."""
import re
import pandas as pd

CODE_RE = re.compile(r'^(\d{4,6})(?:\.(TW|TWO))?$', re.IGNORECASE)

def normalize_codes(raw):
    tokens = re.split(r'[,，;；\s]+', raw.strip())
    seen, result = set(), []
    for token in tokens:
        if not token:
            continue
        match = CODE_RE.fullmatch(token.upper())
        if not match:
            raise ValueError(f'股票代碼格式錯誤：{token}（例如 2330、6488.TWO）')
        code = match.group(1) + ('.' + match.group(2).upper() if match.group(2) else '')
        if code not in seen:
            result.append(code); seen.add(code)
    if len(result) > 20:
        raise ValueError('第一版最多追蹤20檔股票')
    return result

def candidates(code):
    return [code] if '.' in code else [code + '.TW', code + '.TWO']

def fetch(code, period='1y'):
    import yfinance as yf
    errors = []
    for symbol in candidates(code):
        try:
            df = yf.download(symbol, period=period, interval='1d', auto_adjust=True,
                             progress=False, threads=False, timeout=20, multi_level_index=False)
            if not df.empty and all(k in df.columns for k in ['Open','High','Low','Close','Volume']):
                df = df.loc[:, ['Open','High','Low','Close','Volume']].dropna()
                if len(df) >= 70:
                    return symbol, df
            errors.append(f'{symbol}: 資料不足')
        except Exception as e:
            errors.append(f'{symbol}: {type(e).__name__}')
    raise ValueError('無法取得行情：' + ' / '.join(errors))
