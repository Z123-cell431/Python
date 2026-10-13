import argparse
import os
import re
import time
import random
from datetime import datetime

import akshare as ak
import pandas as pd

# 输出目录：导入即自动创建，避免写 CSV 时目录不存在
OUTPUT_DIR = '基金数据分析/数据清洗前'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# akshare fund_open_fund_rank_em 的基金类型映射
FUND_TYPE_MAP = {
    'gp': '股票型', 'hh': '混合型', 'zq': '债券型',
    'zs': '指数型', 'qdii': 'QDII', 'fof': 'FOF',
}


def get_rank_data(fund_type, retries=2):
    """获取指定类型基金排行榜（akshare 一次返回全量），按近一年收益降序。"""
    symbol = FUND_TYPE_MAP[fund_type]
    df = None
    for i in range(retries + 1):
        try:
            df = ak.fund_open_fund_rank_em(symbol=symbol)
            break
        except Exception as e:
            print(f'排行榜获取失败({i + 1}/{retries + 1}): {e}')
            if i < retries:
                time.sleep(random.uniform(1, 2))
    if df is None or df.empty:
        return pd.DataFrame()
    # 只保留与旧版一致的列；akshare 无“成立日期”，多出的“自定义”列丢弃
    keep = ['基金代码', '基金简称', '日期', '单位净值', '累计净值', '日增长率',
            '近1周', '近1月', '近3月', '近6月', '近1年', '近2年', '近3年',
            '今年来', '成立来', '手续费']
    df = df[keep].copy()
    # 按近一年收益降序，无数据的排最后
    df = df.sort_values('近1年', ascending=False, na_position='last')
    # 同一基金可能出现多条份额记录，按基金代码去重
    df = df.drop_duplicates(subset='基金代码').reset_index(drop=True)
    print(f'{symbol}基金共 {len(df)} 只。')
    return df


def _fetch_holdings(fund_code, year, topline=10):
    """获取单只基金最新季度的前十大重仓股，返回 (持仓 DataFrame, 报告期)。"""
    df = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year))
    if df is None or df.empty:
        return pd.DataFrame(), ''
    # 季度列形如 '2026年2季度股票投资明细'，先解析出年份和季度号
    q = df['季度'].str.extract(r'(\d{4})年(\d)季度')
    df = df.assign(_年=pd.to_numeric(q[0], errors='coerce'),
                   _季=pd.to_numeric(q[1], errors='coerce'))
    df = df.dropna(subset=['_年', '_季'])
    if df.empty:
        return pd.DataFrame(), ''
    # 只取最新季度的前 topline 条
    latest_year = int(df['_年'].max())
    sub = df[df['_年'] == latest_year]
    latest_q = int(sub['_季'].max())
    sub = sub[sub['_季'] == latest_q].sort_values('序号').head(topline).copy()
    period = f'{latest_year}年{latest_q}季度'
    # 列名与旧版输出保持一致，clean.py 可直接复用
    sub = sub.rename(columns={'持股数': '持股数（万股）', '持仓市值': '持仓市值（万元）'})
    sub['序号'] = range(1, len(sub) + 1)
    sub['基金代码'] = fund_code
    sub['报告期'] = period
    keep = ['序号', '股票代码', '股票名称', '占净值比例', '持股数（万股）',
            '持仓市值（万元）', '基金代码', '报告期']
    return sub[keep].reset_index(drop=True), period


def _infer_period_tag(df_position_data):
    """从持仓明细的报告期列推断季度标记，如 '2026年2季度'；无数据返回 ''。"""
    if df_position_data.empty or '报告期' not in df_position_data.columns:
        return ''
    s = df_position_data['报告期'].dropna()
    s = s[s != '']
    return s.mode().iloc[0] if not s.empty else ''


def get_position_data(df_rank_data, max_rank, year):
    """爬取前 max_rank 只基金的前十大持仓，返回 (基金详情, 持仓明细)。"""
    codes = df_rank_data['基金代码'].head(max_rank).tolist()
    pos_frames = []
    detail_rows = []
    n = len(codes)
    try:
        for i, code in enumerate(codes, 1):
            try:
                pdf, period = _fetch_holdings(code, year, topline=10)
            except Exception as e:
                print(f'[{i}/{n}] {code} 持仓获取失败: {e}')
                detail_rows.append({'基金代码': code, '持仓报告期': '',
                                    '重仓股数量': 0, '前十大合计占比': None})
                continue
            # 计算前十大合计占比
            top10_sum = pdf['占净值比例'].sum() if not pdf.empty else None
            if not pdf.empty:
                pos_frames.append(pdf)
            detail_rows.append({'基金代码': code, '持仓报告期': period,
                                '重仓股数量': len(pdf), '前十大合计占比': top10_sum})
            print(f'[{i}/{n}] {code} 报告期={period} 持仓={len(pdf)}条')
            time.sleep(random.uniform(0.3, 0.6))
    except KeyboardInterrupt:
        print(f'\n手动中断，已爬取 {len(detail_rows)}/{n} 只基金，保存已完成部分。')
    df_position_data = pd.concat(pos_frames, ignore_index=True) if pos_frames else pd.DataFrame()
    df_rank_detail_data = pd.DataFrame(detail_rows)
    return df_rank_detail_data, df_position_data


# 爬取数据
def get_data(fund_type, year, quarterly='', max_rank=300):
    # 获取基金的收益排名情况
    df_rank_data = get_rank_data(fund_type)
    if df_rank_data.empty:
        print('未获取到排名数据，结束。')
        return 0

    # 获取基金的详细数据和详细的持仓信息
    max_rank = min(max_rank, len(df_rank_data))
    df_rank_detail_data, df_position_data = get_position_data(df_rank_data, max_rank, year)

    # 季度标记未指定时按持仓报告期自动识别，避免文件名与实际数据季度不符
    if not quarterly:
        quarterly = _infer_period_tag(df_position_data) or '未知季度'

    # 合并基金详细数据和持仓详细数据
    df_rank_data = df_rank_data.merge(df_rank_detail_data, on='基金代码', how='left')
    # 仅文本列空缺补 '--'，数值列保留 NaN 以维持数值类型
    obj_cols = df_rank_data.select_dtypes(exclude='number').columns
    df_rank_data[obj_cols] = df_rank_data[obj_cols].fillna('--')

    # 保存数据到 csv 文件
    rate_return_path = os.path.join(
        OUTPUT_DIR, f'{year}年{fund_type}型基金近一年高收益率基金的收益详情.csv')
    position_path = os.path.join(
        OUTPUT_DIR, f'{year}年{fund_type}型基金近一年高收益率基金的前十大持仓{quarterly}.csv')
    df_rank_data.to_csv(rate_return_path, encoding='utf-8-sig', index=False)
    df_position_data.to_csv(position_path, encoding='utf-8-sig', index=False)
    print(f'数据爬取完成！收益详情 -> {rate_return_path}')
    print(f'持仓明细 -> {position_path}')
    return max_rank


# 主程序
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='基于 akshare 的天天基金近一年高收益率基金收益与持仓爬取')
    parser.add_argument('--fund-type', default='gp', choices=list(FUND_TYPE_MAP),
                        help='gp=股票型，hh=混合型，zq=债券型，zs=指数型，qdii=QDII，fof=FOF')
    parser.add_argument('--max-rank', type=int, default=300, help='抓取持仓详情的基金数量上限')
    parser.add_argument('--year', default=str(datetime.now().year),
                        help='持仓数据年份，同时作为输出文件名中的年份标记')
    parser.add_argument('--quarterly', default='',
                        help='输出文件名中的季度标记，留空则按持仓报告期自动识别')
    args = parser.parse_args()
    if not re.fullmatch(r'\d{4}', args.year):
        parser.error(f'--year 必须是4位年份，收到: {args.year!r}')

    t0 = time.time()
    max_rank = get_data(args.fund_type, args.year, args.quarterly, args.max_rank)
    print(f'共爬取基金数: {max_rank}，耗时 {time.time() - t0:.1f}s')
