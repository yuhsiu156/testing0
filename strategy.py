"""Pure indicator/signal logic; all reference windows exclude signal day."""
from dataclasses import dataclass
import pandas as pd
import numpy as np

@dataclass(frozen=True)
class Settings:
    base_days: int = 30
    max_base_pct: float = 20.0
    vol_days: int = 20
    min_vol_ratio: float = 1.5
    max_chase_pct: float = 5.0
    recent_days: int = 10
    early_days: int = 20
    compression_ratio: float = 0.85
    near_pct: float = 3.0

    def validate(self):
        if self.base_days < 2 or self.vol_days < 1 or self.recent_days < 2 or self.early_days < 2:
            raise ValueError('觀察天數設定錯誤')
        if self.max_base_pct <= 0 or self.min_vol_ratio <= 1 or self.max_chase_pct <= 0:
            raise ValueError('整理區間、突破量比及追價幅度設定不正確')
        if not (0 < self.compression_ratio < 1) or self.near_pct <= 0:
            raise ValueError('量縮比須介於0與1，接近突破百分比須大於0')


def evaluate(df: pd.DataFrame, s: Settings) -> dict:
    s.validate()
    df = df.copy().sort_index().dropna(subset=['Open','High','Low','Close','Volume'])
    required = max(s.base_days, s.vol_days, 60, s.recent_days + s.early_days, 25) + 6
    if len(df) < required:
        raise ValueError(f'歷史資料不足，至少需要 {required} 個交易日')
    close = df['Close'].astype(float)
    high = df['High'].astype(float)
    low = df['Low'].astype(float)
    volume = df['Volume'].astype(float)
    if (close <= 0).any() or (low <= 0).any():
        raise ValueError('價格資料異常')
    # Exclude current bar from baselines.
    pivot = high.shift(1).rolling(s.base_days).max().iloc[-1]
    base_low = low.shift(1).rolling(s.base_days).min().iloc[-1]
    prior_vol = volume.shift(1).rolling(s.vol_days).mean().iloc[-1]
    # Prior 10 days compared with 20 days immediately before those 10 days.
    recent_vol = volume.shift(1).rolling(s.recent_days).mean().iloc[-1]
    old_vol = volume.shift(s.recent_days + 1).rolling(s.early_days).mean().iloc[-1]
    # Price contraction: prior 10-day range / prior 30-day range.
    recent_hi = high.shift(1).rolling(s.recent_days).max().iloc[-1]
    recent_lo = low.shift(1).rolling(s.recent_days).min().iloc[-1]
    base_width = (pivot / base_low - 1) * 100
    recent_width = (recent_hi / recent_lo - 1) * 100
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    ma20_prev = close.shift(5).rolling(20).mean().iloc[-1]
    c = float(close.iloc[-1]); v = float(volume.iloc[-1])
    breakout_pct = (c / pivot - 1) * 100
    vol_ratio = v / prior_vol if prior_vol > 0 else 0.0
    contraction = recent_vol / old_vol if old_vol > 0 else float('inf')
    # Day's volume not included in reduced-volume test; recently tightening price range required.
    checks = {
        '底部整理': bool(base_width <= s.max_base_pct),
        '量縮價穩': bool(contraction <= s.compression_ratio and recent_width < base_width),
        '帶量突破': bool(c > pivot and vol_ratio >= s.min_vol_ratio),
        '均線趨勢': bool(c > ma20 and c > ma60 and ma20 > ma20_prev),
        '避免追高': bool(c > pivot and breakout_pct <= s.max_chase_pct),
    }
    all_good = all(checks.values())
    # Near-breakout category explicitly does not require current breakout volume.
    near = (checks['底部整理'] and checks['量縮價穩'] and checks['均線趨勢']
            and -s.near_pct <= breakout_pct <= 0)
    status = '符合突破' if all_good else ('接近突破' if near else ('整理中' if checks['底部整理'] else '不符合'))
    return {
        '日期': str(df.index[-1].date()) if hasattr(df.index[-1], 'date') else str(df.index[-1])[:10],
        '收盤價': round(c, 2), '突破價': round(float(pivot), 2),
        '整理幅度%': round(float(base_width), 2), '近期整理幅度%': round(float(recent_width), 2),
        '突破量比': round(float(vol_ratio), 2), '量縮比': round(float(contraction), 2),
        '距突破價%': round(float(breakout_pct), 2),
        '近5日漲幅%': round(float((c / close.iloc[-6] - 1) * 100), 2),
        '20日均線': round(float(ma20), 2), '60日均線': round(float(ma60), 2),
        '通過數': sum(checks.values()), '狀態': status,
        **{f'條件_{k}': value for k, value in checks.items()},
    }


def trend_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df[['Close', 'Volume']].copy()
    out['MA20'] = out['Close'].rolling(20).mean()
    out['MA60'] = out['Close'].rolling(60).mean()
    return out.tail(120)
