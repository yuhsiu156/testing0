import json
from pathlib import Path
import pandas as pd
import streamlit as st
from data_source import normalize_codes, fetch
from strategy import Settings, evaluate, trend_frame

st.set_page_config(page_title='台股五條件監控', page_icon='📈', layout='wide')
st.title('📈 台股五條件突破監控')
st.caption('盤後追蹤 · 20檔上限 · Yahoo Finance 還原日線；資料可能延遲，僅供研究觀察，非投資建議')
DEFAULT = Path('watchlist.txt').read_text(encoding='utf-8').strip() if Path('watchlist.txt').exists() else '2330\n2317\n2454'
with st.sidebar:
    st.header('自選股清單')
    raw = st.text_area('代碼以逗號、空格或換行分隔', value=DEFAULT, height=180,
                       help='上市 2330 或 2330.TW；上櫃可寫 6488.TWO；未附後綴時先查上市再查上櫃')
    st.download_button('下載目前名單', data=raw, file_name='watchlist.txt', mime='text/plain')
    st.caption('網頁內編輯是暫時性的。長期固定追蹤，請同步修改 GitHub 專案的 watchlist.txt。')
    st.header('策略參數')
    base_days = st.number_input('整理觀察天數', 10, 120, 30)
    max_base_pct = st.slider('整理最大幅度 %', 5., 50., 20., 1.)
    vol_days = st.number_input('基準均量天數', 5, 90, 20)
    min_vol_ratio = st.slider('突破最低量比', 1.1, 5., 1.5, .1)
    max_chase_pct = st.slider('最大追高幅度 %', 1., 15., 5., .5)
    compression_ratio = st.slider('近期量縮比上限', .3, .99, .85, .01)
    near_pct = st.slider('接近突破距離 %', 1., 10., 3., .5)
    st.caption('量縮：前10日均量 ≤ 更早20日均量 × 量縮比；價穩：前10日高低幅度小於前30日。均線：收盤高於20/60日線且20日線高於5日前。')

try:
    codes = normalize_codes(raw)
except ValueError as e:
    st.error(str(e)); st.stop()
if not codes:
    st.info('請先輸入至少一檔股票代碼。'); st.stop()
s = Settings(base_days=int(base_days), max_base_pct=max_base_pct, vol_days=int(vol_days),
             min_vol_ratio=min_vol_ratio, max_chase_pct=max_chase_pct,
             compression_ratio=compression_ratio, near_pct=near_pct)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(code):
    return fetch(code)

results, errors, frames = [], [], {}
bar = st.progress(0, text='讀取日線資料...')
for i, code in enumerate(codes):
    try:
        symbol, df = cached_fetch(code)
        row = evaluate(df, s); row['股票'] = symbol
        results.append(row); frames[symbol] = df
    except Exception as e:
        errors.append({'股票': code, '原因': str(e)})
    bar.progress((i+1)/len(codes), text=f'已完成 {i+1}/{len(codes)}')
bar.empty()

if results:
    table = pd.DataFrame(results)
    cols = st.columns(4)
    cols[0].metric('追蹤檔數', len(codes))
    cols[1].metric('符合突破', int((table['狀態'] == '符合突破').sum()))
    cols[2].metric('接近突破', int((table['狀態'] == '接近突破').sum()))
    cols[3].metric('資料取得成功', len(results))
    order = {'符合突破':0, '接近突破':1,'整理中':2,'不符合':3}
    table = table.assign(_order=table['狀態'].map(order)).sort_values(['_order','通過數'], ascending=[True,False]).drop(columns=['_order'])
    st.subheader('今日監控表')
    visible = ['股票','日期','收盤價','突破價','狀態','通過數','整理幅度%','量縮比','突破量比','距突破價%','近5日漲幅%']
    st.dataframe(table[visible], hide_index=True, use_container_width=True)
    st.download_button('下載完整訊號 CSV', table.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), 'stock_signals.csv', 'text/csv')
    st.subheader('個股條件明細')
    selected = st.selectbox('選擇股票', table['股票'].to_list())
    item = table.loc[table['股票'] == selected].iloc[0]
    conditions = ['底部整理','量縮價穩','帶量突破','均線趨勢','避免追高']
    checks = pd.DataFrame({'條件': conditions, '結果': ['✅ 通過' if item[f'條件_{k}'] else '❌ 未通過' for k in conditions]})
    st.dataframe(checks, hide_index=True, use_container_width=True)
    st.line_chart(trend_frame(frames[selected])[['Close','MA20','MA60']], y_label='價格')
    st.bar_chart(trend_frame(frames[selected])[['Volume']], y_label='成交量（股）')
    st.caption(f"資料最後交易日：{item['日期']}。突破價每日更新，並非持倉固定停損價。")
else:
    st.warning('沒有成功讀取任何股票，請稍後重試或確認代碼。')
if errors:
    with st.expander(f'無法分析的股票（{len(errors)}）'):
        st.dataframe(pd.DataFrame(errors), hide_index=True, use_container_width=True)
st.divider()
st.caption('資料來源：Yahoo Finance / yfinance，非交易所保證的即時或正式報價。股價使用 auto_adjust=True 調整歷史 OHLC；成交量保留供應商提供值。此策略只是篩選條件，非獲利保證。')
