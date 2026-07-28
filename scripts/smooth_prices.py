"""
smooth_prices.py — 专业级房价数据平滑引擎
基于统计方法检测并修正数据源切换导致的价格异常

检测方法:
1. MAD异常值检测 — 基于中位数绝对偏差的环比异常识别
2. 脉冲反转检测 — 涨了立刻跌回(或反向), 数据源切换典型特征
3. 水平断裂检测 — 相邻月份突变超过动态阈值
4. 源切换月份增强 — 已知的系统性数据源切换月份额外关注

修正方法: 异常区间两端锚定, 中间线性插值, 迭代收敛
"""
import json
import os
import statistics

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

KNOWN_SWITCH_MONTHS = {'2024/08', '2025/08', '2026/01'}

PULSE_THRESHOLD = 0.04
LEVEL_SHIFT_THRESHOLD = 0.12
MAD_MULTIPLIER = 4.5
MAX_ROUNDS = 5

NATIONAL_SWITCH_WINDOW = 3
NATIONAL_TRANSITION_MONTHS = 4


def smooth_national_prices(prices, months):
    """全国均价专用平滑: 源切换过渡期斜率渐变

    问题: 安居客每年只有8-12月, 1月消失时全国均价下跌斜率突然变缓,
    8月加入时突然变陡. 单月修正不够, 因为偏差持续到下次源变化.

    方法: 在切换月份, 用前窗口趋势率作为基准, 然后在过渡期内从基准率
    渐变到实际率, 避免斜率突变. 过渡期后回到实际数据.
    """
    if not prices or len(prices) < 5:
        return prices, 0

    result = list(prices)
    fixed = 0
    w = NATIONAL_SWITCH_WINDOW
    transition = NATIONAL_TRANSITION_MONTHS

    raw_rates = []
    for i in range(1, len(result)):
        if result[i - 1] > 0:
            raw_rates.append(result[i] / result[i - 1])
        else:
            raw_rates.append(1.0)

    for idx, m in enumerate(months):
        if m not in KNOWN_SWITCH_MONTHS:
            continue
        if idx < w or idx >= len(result) - 1:
            continue

        rate_idx = idx - 1
        before_rates = raw_rates[max(0, rate_idx - w):rate_idx]

        if not before_rates:
            continue

        pre_trend = sum(before_rates) / len(before_rates)
        actual_rate = raw_rates[rate_idx]
        deviation = actual_rate - pre_trend

        if abs(deviation) < 0.002:
            continue

        for t in range(transition + 1):
            ri = rate_idx + t
            if ri >= len(raw_rates):
                break

            blend = t / transition
            blended_rate = pre_trend + (raw_rates[ri] - pre_trend) * blend
            raw_rates[ri] = blended_rate

        result[idx] = round(result[idx - 1] * raw_rates[rate_idx])
        fixed += 1

        for j in range(idx + 1, len(result)):
            if j - 1 < len(raw_rates):
                result[j] = round(result[j - 1] * raw_rates[j - 1])

    return result, fixed

    return result, fixed


def compute_mom_rates(prices):
    """计算环比变化率序列"""
    rates = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            rates.append((prices[i] - prices[i - 1]) / prices[i - 1])
        else:
            rates.append(0.0)
    return rates


def mad_outliers(rates, multiplier=MAD_MULTIPLIER):
    """MAD (Median Absolute Deviation) 异常值检测
    比标准差更稳健, 不受极端值影响"""
    if len(rates) < 5:
        return set()
    median = statistics.median(rates)
    abs_devs = [abs(r - median) for r in rates]
    mad = statistics.median(abs_devs)
    if mad < 0.001:
        mad = 0.001
    threshold = multiplier * mad * 1.4826
    outliers = set()
    for i, r in enumerate(rates):
        if abs(r - median) > threshold:
            outliers.add(i + 1)
    return outliers


def find_anomalies(prices, months=None):
    """综合异常检测: MAD + 脉冲 + 水平断裂 + 源切换月份"""
    if not prices or len(prices) < 3:
        return set()

    bad = set()
    rates = compute_mom_rates(prices)

    bad.update(mad_outliers(rates))

    for i in range(1, len(prices) - 1):
        chg1 = (prices[i] - prices[i - 1]) / prices[i - 1] if prices[i - 1] > 0 else 0
        chg2 = (prices[i + 1] - prices[i]) / prices[i] if prices[i] > 0 else 0
        if chg1 * chg2 < 0 and abs(chg1) > PULSE_THRESHOLD and abs(chg2) > PULSE_THRESHOLD:
            bad.add(i)

    for i in range(1, len(prices)):
        chg = abs((prices[i] - prices[i - 1]) / prices[i - 1]) if prices[i - 1] > 0 else 0
        if chg > LEVEL_SHIFT_THRESHOLD:
            bad.add(i)

    if months:
        for i, m in enumerate(months):
            if m in KNOWN_SWITCH_MONTHS and i > 0:
                chg = abs((prices[i] - prices[i - 1]) / prices[i - 1]) if prices[i - 1] > 0 else 0
                if chg > 0.05:
                    bad.add(i)

    return bad


def smooth(prices, months=None):
    """迭代平滑: 检测异常 → 锚点插值 → 重新检测, 直到收敛"""
    if not prices or len(prices) < 3:
        return prices, 0

    result = list(prices)
    total_fixed = 0

    for _round in range(MAX_ROUNDS):
        bad = find_anomalies(result, months)
        if not bad:
            break

        round_fixed = 0
        for i in sorted(bad):
            left = i - 1
            while left in bad and left > 0:
                left -= 1
            right = i + 1
            while right in bad and right < len(result) - 1:
                right += 1

            if left not in bad and right not in bad and right > left and right < len(result):
                for j in range(left + 1, right):
                    ratio = (j - left) / (right - left)
                    new_val = round(result[left] + (result[right] - result[left]) * ratio)
                    if new_val != result[j]:
                        result[j] = new_val
                        round_fixed += 1

        total_fixed += round_fixed
        if round_fixed == 0:
            break

    return result, total_fixed


def main():
    summary_path = os.path.join(DATA_DIR, 'summary.json')
    with open(summary_path) as f:
        summary = json.load(f)

    months = summary['meta']['months']
    total_fixed = 0
    affected_cities = []

    for name, city in summary['cities'].items():
        original = list(city['prices'])
        smoothed, count = smooth(city['prices'], months)
        if count > 0:
            city['prices'] = smoothed
            affected_cities.append((name, count, original, smoothed))
            total_fixed += count

    all_prices = [c['prices'] for c in summary['cities'].values()]
    n_months = len(months)
    nat_prices = []
    for m in range(n_months):
        vals = [p[m] for p in all_prices if m < len(p)]
        nat_prices.append(round(sum(vals) / len(vals)))

    nat_smoothed, nat_fixed = smooth_national_prices(nat_prices, months)
    summary['national']['prices'] = nat_smoothed

    with open(summary_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))

    city_dir = os.path.join(DATA_DIR, 'city')
    city_files = summary['meta'].get('city_files', {})

    for name, city in summary['cities'].items():
        code = city_files.get(name, name)
        city_path = os.path.join(city_dir, f'{code}.json')
        if os.path.exists(city_path):
            with open(city_path) as f:
                detail = json.load(f)
            detail['prices'] = city['prices']
            detail['volumes'] = city['volumes']
            with open(city_path, 'w') as f:
                json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))

    print(f'[SMOOTH] 平滑完成: {len(affected_cities)}个城市, 共{total_fixed}个数据点')
    if affected_cities:
        print()
        for name, count, orig, smoothed in affected_cities:
            diffs = []
            for i in range(len(orig)):
                if orig[i] != smoothed[i]:
                    m = months[i] if i < len(months) else f'[{i}]'
                    pct = round((orig[i] - smoothed[i]) / smoothed[i] * 100, 1)
                    diffs.append(f'{m}: {orig[i]}→{smoothed[i]}({pct:+.1f}%)')
            print(f'  {name} ({count}点): {", ".join(diffs[:8])}')
            if len(diffs) > 8:
                print(f'    ... 还有{len(diffs)-8}个修正点')

    print(f'\n[SMOOTH] 文件已更新: summary.json + {len(city_files)}个城市文件')
    if nat_fixed:
        print(f'[SMOOTH] 全国均价源切换平滑: {nat_fixed}个月份修正')


if __name__ == '__main__':
    main()
