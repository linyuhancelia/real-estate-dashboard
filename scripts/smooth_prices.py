"""
smooth_prices.py — 全量城市数据清洗引擎

三层防线:
1. 城市级异常检测 — 绝对环比上限 + 偏离全城中位数 + 脉冲反转 + MAD
2. 城市级插值修复 — 异常区间两端锚定, 中间线性插值, 迭代收敛
3. 全国级过渡平滑 — 源切换月份斜率渐变, 消除系统性台阶
"""
import json
import os
import statistics

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

KNOWN_SWITCH_MONTHS = {'2024/08', '2025/08', '2026/01'}

MAX_ABS_MOM = 0.025
MAX_DEVIATION_FROM_MEDIAN = 0.025
PULSE_THRESHOLD = 0.02
MAD_MULTIPLIER = 3.5
MAX_ROUNDS = 8

NATIONAL_SWITCH_WINDOW = 3
NATIONAL_TRANSITION_MONTHS = 4


def compute_mom_rates(prices):
    rates = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0:
            rates.append((prices[i] - prices[i - 1]) / prices[i - 1])
        else:
            rates.append(0.0)
    return rates


def mad_outliers(rates, multiplier=MAD_MULTIPLIER):
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


def find_anomalies(prices, months=None, national_medians=None):
    """综合异常检测

    检测条件 (满足任一即标记):
    1. |环比| > 2.5% (城市均价不应有这么大的月波动)
    2. |城市环比 - 全城中位数| > 2.5% (偏离大盘过远)
    3. 脉冲反转: 涨了立刻跌(或反向), 且幅度 > 2%
    4. MAD统计异常值 (3.5倍MAD)
    """
    if not prices or len(prices) < 3:
        return set()

    bad = set()
    rates = compute_mom_rates(prices)

    for i, r in enumerate(rates):
        idx = i + 1
        if abs(r) > MAX_ABS_MOM:
            bad.add(idx)

        if national_medians and i < len(national_medians):
            if abs(r - national_medians[i]) > MAX_DEVIATION_FROM_MEDIAN:
                bad.add(idx)

    for i in range(1, len(prices) - 1):
        chg1 = (prices[i] - prices[i - 1]) / prices[i - 1] if prices[i - 1] > 0 else 0
        chg2 = (prices[i + 1] - prices[i]) / prices[i] if prices[i] > 0 else 0
        if chg1 * chg2 < 0 and abs(chg1) > PULSE_THRESHOLD and abs(chg2) > PULSE_THRESHOLD:
            bad.add(i)

    bad.update(mad_outliers(rates))

    return bad


def smooth(prices, months=None, national_medians=None):
    """迭代平滑: 检测异常 → 锚点插值 → 重新检测, 直到收敛"""
    if not prices or len(prices) < 3:
        return prices, 0

    result = list(prices)
    total_fixed = 0

    for _round in range(MAX_ROUNDS):
        bad = find_anomalies(result, months, national_medians)
        if not bad:
            break

        round_fixed = 0
        sorted_bad = sorted(bad)

        for i in sorted_bad:
            left = i - 1
            while left in bad and left > 0:
                left -= 1
            right = i + 1
            while right in bad and right < len(result) - 1:
                right += 1

            if left >= 0 and left not in bad and right < len(result) and right not in bad and right > left:
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


def smooth_national_prices(prices, months):
    """全国均价专用平滑: 源切换过渡期斜率渐变"""
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
            raw_rates[ri] = pre_trend + (raw_rates[ri] - pre_trend) * blend

        result[idx] = round(result[idx - 1] * raw_rates[rate_idx])
        fixed += 1

        for j in range(idx + 1, len(result)):
            if j - 1 < len(raw_rates):
                result[j] = round(result[j - 1] * raw_rates[j - 1])

    return result, fixed


def full_clean(summary):
    """全量清洗: 所有城市 + 全国均价, 返回修改统计"""
    months = summary['meta']['months']
    n_months = len(months)
    city_files = summary['meta'].get('city_files', {})
    city_dir = os.path.join(DATA_DIR, 'city')

    # Pass 1: compute national median MoM per month (for cross-city comparison)
    all_rates = []
    for city in summary['cities'].values():
        rates = compute_mom_rates(city['prices'])
        all_rates.append(rates)

    national_medians = []
    for mi in range(n_months - 1):
        month_rates = [r[mi] for r in all_rates if mi < len(r)]
        national_medians.append(statistics.median(month_rates))

    # Pass 2: smooth all cities using national medians as reference
    results = []
    total_points = 0
    for name, city in summary['cities'].items():
        original = list(city['prices'])
        smoothed, count = smooth(city['prices'], months, national_medians)
        if count > 0:
            city['prices'] = smoothed
            total_points += count

            code = city_files.get(name, name)
            city_path = os.path.join(city_dir, f'{code}.json')
            if os.path.exists(city_path):
                with open(city_path) as f:
                    detail = json.load(f)
                detail['prices'] = smoothed
                with open(city_path, 'w') as f:
                    json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))

            def max_mom(p):
                return max(abs((p[i]-p[i-1])/p[i-1]) for i in range(1,len(p)) if p[i-1]>0)
            results.append((name, count, max_mom(original)*100, max_mom(smoothed)*100))

    # Pass 3: recompute national average
    all_prices = [c['prices'] for c in summary['cities'].values()]
    nat_prices = []
    for m in range(n_months):
        vals = [p[m] for p in all_prices if m < len(p) and p[m] > 0]
        nat_prices.append(round(sum(vals) / len(vals)))

    # Pass 4: national transition smoothing
    nat_smoothed, nat_fixed = smooth_national_prices(nat_prices, months)
    summary['national']['prices'] = nat_smoothed

    return results, total_points, nat_fixed


def main():
    summary_path = os.path.join(DATA_DIR, 'summary.json')
    with open(summary_path) as f:
        summary = json.load(f)

    results, total_points, nat_fixed = full_clean(summary)

    with open(summary_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))

    print(f'[CLEAN] 完成: {len(results)}个城市, {total_points}个数据点修正')
    if results:
        results.sort(key=lambda x: x[3] - x[2])
        for name, count, old_mm, new_mm in results:
            print(f'  {name}: {count}点, maxMoM {old_mm:.1f}%→{new_mm:.1f}%')

    if nat_fixed:
        print(f'[CLEAN] 全国均价过渡平滑: {nat_fixed}个月份')

    # Update bundled JS
    bundled_path = os.path.join(os.path.dirname(DATA_DIR), 'miniprogram', 'data', 'bundled_summary.js')
    if os.path.exists(os.path.dirname(bundled_path)):
        js = 'module.exports = ' + json.dumps(summary, ensure_ascii=False, separators=(',', ':'))
        with open(bundled_path, 'w') as f:
            f.write(js)
        print(f'[CLEAN] bundled_summary.js ({len(js)//1024}KB)')

    city_files = summary['meta'].get('city_files', {})
    print(f'[CLEAN] 文件已更新: summary.json + bundled + {len(city_files)}个城市文件')


if __name__ == '__main__':
    main()
