import glob
import os
import re

import pandas as pd

INPUT_DIR = '基金数据分析/数据清洗前'
OUTPUT_DIR = '基金数据分析/数据清洗后'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _to_number(s):
    """去掉 % 和千分位逗号后转数值，'--' 等无效值转 NaN。"""
    return pd.to_numeric(
        s.astype(str).str.replace('%', '', regex=False).str.replace(',', '', regex=False),
        errors='coerce')


def clean_rank_data(path):
    """清洗收益详情：数值列规范化、日期解析、文本去空格。"""
    df = pd.read_csv(path, dtype={'基金代码': str})
    df['基金简称'] = df['基金简称'].str.strip()

    # 收益列可能含 '--'（成立时间不足的基金），统一转数值
    num_cols = ['单位净值', '累计净值', '日增长率', '近1周', '近1月', '近3月',
                '近6月', '近1年', '近2年', '近3年', '今年来', '成立来']
    for c in num_cols:
        if c in df.columns:
            df[c] = _to_number(df[c])

    # 手续费：'1.50%' -> 1.5，缺失保持 NaN
    if '手续费' in df.columns:
        df['手续费'] = _to_number(df['手续费'])

    # 日期列解析为日期类型
    for c in ['日期', '成立日期']:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce').dt.date

    df = df.drop_duplicates(subset='基金代码').reset_index(drop=True)
    return df


def clean_position_data(path):
    """清洗前十大持仓：删空列、比例/金额转数值、报告期拆列。"""
    df = pd.read_csv(path, dtype={'基金代码': str, '股票代码': str})

    # 最新价/涨跌幅爬取时全空，相关资讯为无效拼接文本，直接删除
    df = df.drop(columns=[c for c in ['最新价', '涨跌幅', '相关资讯'] if c in df.columns])

    # 占净值比例 '8.29%' -> 8.29；市值含千分位逗号 '36,976.08' -> 36976.08
    for c in ['占净值比例', '持股数（万股）', '持仓市值（万元）']:
        if c in df.columns:
            df[c] = _to_number(df[c])

    # 股票代码保留原始字符串（A股6位、港股5位，不补零）
    df['股票代码'] = df['股票代码'].str.strip()
    df['股票名称'] = df['股票名称'].str.strip()

    # 报告期 '2026年2季度' 拆出年份和季度，方便按季度分组统计
    if '报告期' in df.columns:
        m = df['报告期'].str.extract(r'(\d{4})年([1-4])季度')
        df['报告年份'] = pd.to_numeric(m[0], errors='coerce').astype('Int64')
        df['报告季度'] = pd.to_numeric(m[1], errors='coerce').astype('Int64')

    df = df.drop_duplicates(subset=['基金代码', '股票代码', '报告期']).reset_index(drop=True)
    return df


def clean_all(input_dir=INPUT_DIR, output_dir=OUTPUT_DIR):
    """按文件名模式分发清洗输入目录下的全部 CSV，同名输出到清洗后目录。"""
    files = sorted(glob.glob(os.path.join(input_dir, '*.csv')))
    if not files:
        print(f'{input_dir} 下没有 CSV 文件。')
        return
    for path in files:
        name = os.path.basename(path)
        if '收益详情' in name:
            df = clean_rank_data(path)
        elif '持仓' in name:
            df = clean_position_data(path)
        else:
            print(f'跳过无法识别的文件: {name}')
            continue
        out_path = os.path.join(output_dir, name)
        df.to_csv(out_path, encoding='utf-8-sig', index=False)
        print(f'{name}: {len(df)} 行 -> {out_path}')
    print('数据清洗完成！')


if __name__ == '__main__':
    # 只筛选文件名带2026年的两份文件
    rank_files = glob.glob(os.path.join(INPUT_DIR, "*2026年*收益详情*.csv"))
    pos_files = glob.glob(os.path.join(INPUT_DIR, "*2026年*前十大持仓*.csv"))

    # 清洗收益详情文件
    if rank_files:
        file_path = rank_files[0]
        file_name = os.path.basename(file_path)
        df = clean_rank_data(file_path)
        out_path = os.path.join(OUTPUT_DIR, file_name)
        df.to_csv(out_path, encoding='utf-8-sig', index=False)
        print(f"✅已清洗收益文件：{file_name}，共{len(df)}行")
    else:
        print("❌没有找到2026年收益详情csv")

    # 清洗前十大持仓文件
    if pos_files:
        file_path = pos_files[0]
        file_name = os.path.basename(file_path)
        df = clean_position_data(file_path)
        out_path = os.path.join(OUTPUT_DIR, file_name)
        df.to_csv(out_path, encoding='utf-8-sig', index=False)
        print(f"✅已清洗持仓文件：{file_name}，共{len(df)}行")
    else:
        print("❌没有找到2026年前十大持仓csv")

    print("\n=====2026两份新文件清洗任务结束=====")

