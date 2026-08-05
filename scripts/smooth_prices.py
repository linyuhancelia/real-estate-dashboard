"""
smooth_prices.py — 全量城市数据清洗引擎 v5 (NBS校验层)

核心算法: 首月锚定 + NBS权威率替代 + 前向率重建

v5 升级要点:
- NBS 70城二手住宅月度环比作为权威数据源
- 对于NBS覆盖的城市: 直接使用NBS环比率替代爬虫率
- 对于非NBS城市: 保持v4逻辑(率clamp + 前向邻居替换)
- NBS数据未覆盖的月份(如2026/07+): 回退到v4逻辑

效果:
- 彻底消除"数据源切换造成的方向性错误"
- 广州等一线城市走势与官方数据完全一致
- 西宁等二三线城市使用城市级均值校正方向
"""
import json
import os
import statistics

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

MAX_MOM = 0.02  # 单月环比硬上限 ±2% (仅用于非NBS城市)


def load_nbs_data():
    """加载NBS 70城校验数据."""
    nbs_path = os.path.join(DATA_DIR, 'nbs_70city.json')
    if not os.path.exists(nbs_path):
        return None
    with open(nbs_path) as f:
        return json.load(f)


def get_city_tier(city_name, nbs):
    """确定城市所属层级."""
    if not nbs:
        return None
    for tier, cities in nbs['tier_cities'].items():
        if city_name in cities:
            return tier
    return None


def get_nbs_rate(city_name, month_key, nbs):
    """获取某城市某月的NBS环比率.

    优先级: 城市专项数据 > 层级均值 > None(无数据)
    """
    if not nbs or month_key not in nbs['monthly_rates']:
        return None

    month_data = nbs['monthly_rates'][month_key]

    if city_name in month_data.get('cities', {}):
        return month_data['cities'][city_name]

    tier = get_city_tier(city_name, nbs)
    if tier and tier in month_data.get('tier_avg', {}):
        return month_data['tier_avg'][tier]

    return None


def extract_and_clean_rates(prices):
    """从原始序列提取环比率, 异常率替换为前向趋势 (v4逻辑, 用于非NBS城市)."""
    rates = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            rates.append(prices[i] / prices[i - 1] - 1)
        else:
            rates.append(0.0)

    cleaned = list(rates)
    for i in range(len(cleaned)):
        if abs(cleaned[i]) > MAX_MOM:
            neighbors = []
            for j in range(max(0, i - 6), i):
                if abs(rates[j]) <= MAX_MOM:
                    neighbors.append(rates[j])
            if neighbors:
                cleaned[i] = statistics.median(neighbors)
            else:
                for j in range(i + 1, min(len(rates), i + 4)):
                    if abs(rates[j]) <= MAX_MOM:
                        cleaned[i] = rates[j]
                        break
                else:
                    cleaned[i] = 0.0

    return cleaned


def extract_and_clean_rates_nbs(prices, months, city_name, nbs):
    """NBS校验版: 对NBS覆盖月份直接替换率, 非覆盖月份走v4逻辑."""
    rates = []
    for i in range(1, len(prices)):
        if prices[i - 1] > 0 and prices[i] > 0:
            rates.append(prices[i] / prices[i - 1] - 1)
        else:
            rates.append(0.0)

    cleaned = list(rates)
    nbs_replaced = 0

    for i in range(len(cleaned)):
        month_key = months[i + 1] if (i + 1) < len(months) else None
        nbs_rate = get_nbs_rate(city_name, month_key, nbs) if month_key else None

        if nbs_rate is not None:
            cleaned[i] = nbs_rate
            nbs_replaced += 1
        elif abs(cleaned[i]) > MAX_MOM:
            neighbors = []
            for j in range(max(0, i - 6), i):
                if abs(rates[j]) <= MAX_MOM:
                    neighbors.append(rates[j])
            if neighbors:
                cleaned[i] = statistics.median(neighbors)
            else:
                for j in range(i + 1, min(len(rates), i + 4)):
                    if abs(rates[j]) <= MAX_MOM:
                        cleaned[i] = rates[j]
                        break
                else:
                    cleaned[i] = 0.0

    return cleaned, nbs_replaced


def rebuild_from_anchor(anchor_price, rates):
    """从锚点价格出发, 用cleaned rates前向重建序列."""
    result = [anchor_price]
    for rate in rates:
        clamped = max(-MAX_MOM, min(MAX_MOM, rate))
        result.append(round(result[-1] * (1 + clamped)))
    return result


def rebuild_from_anchor_nbs(anchor_price, rates):
    """NBS版重建: NBS率不做clamp (NBS数据本身就是权威的)."""
    result = [anchor_price]
    for rate in rates:
        result.append(round(result[-1] * (1 + rate)))
    return result


def smooth_city(prices, months=None, city_name=None, nbs=None):
    """对单个城市完整清洗."""
    if not prices or len(prices) < 3:
        return list(prices), 0, 0

    anchor = prices[0]
    if anchor <= 0:
        for i, p in enumerate(prices):
            if p > 0:
                anchor = p
                break
        else:
            return list(prices), 0, 0

    tier = get_city_tier(city_name, nbs) if city_name and nbs else None

    if tier and months:
        rates, nbs_count = extract_and_clean_rates_nbs(prices, months, city_name, nbs)
        rebuilt = rebuild_from_anchor_nbs(anchor, rates)
    else:
        rates = extract_and_clean_rates(prices)
        rebuilt = rebuild_from_anchor(anchor, rates)
        nbs_count = 0

    fixes = sum(1 for a, b in zip(prices, rebuilt) if a != b)
    return rebuilt, fixes, nbs_count


def full_clean(summary):
    """全量清洗: 所有城市 + 全国均价重算."""
    months = summary['meta']['months']
    n_months = len(months)
    city_files = summary['meta'].get('city_files', {})
    city_dir = os.path.join(DATA_DIR, 'city')

    nbs = load_nbs_data()
    if nbs:
        print(f'[v5] NBS校验层加载成功: {len(nbs["monthly_rates"])}个月数据')
    else:
        print('[v5] NBS数据未找到, 回退到v4纯算法模式')

    results = []
    total_fixes = 0
    total_nbs = 0

    for name, city in summary['cities'].items():
        smoothed, fixes, nbs_count = smooth_city(city['prices'], months, name, nbs)

        if fixes > 0:
            city['prices'] = smoothed
            total_fixes += fixes
            results.append((name, fixes, nbs_count))
            total_nbs += nbs_count

            code = city_files.get(name, name)
            city_path = os.path.join(city_dir, f'{code}.json')
            if os.path.exists(city_path):
                with open(city_path) as f:
                    detail = json.load(f)
                detail['prices'] = smoothed
                with open(city_path, 'w') as f:
                    json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))

    # Recompute national average from cleaned city data
    all_prices = [c['prices'] for c in summary['cities'].values()]
    nat_prices = []
    for m in range(n_months):
        vals = [p[m] for p in all_prices if m < len(p) and p[m] > 0]
        nat_prices.append(round(sum(vals) / len(vals)) if vals else 0)

    nat_smoothed, nat_fixes, _ = smooth_city(nat_prices, months, '全国', nbs)
    summary['national']['prices'] = nat_smoothed

    return results, total_fixes, nat_fixes, total_nbs


def main():
    summary_path = os.path.join(DATA_DIR, 'summary.json')

    latest_path = os.path.join(DATA_DIR, 'latest.json')
    if os.path.exists(latest_path):
        print('[v5] 使用 latest.json (原始爬虫数据) 作为输入')
        with open(latest_path) as f:
            summary = json.load(f)
    else:
        print('[v5] latest.json 不存在, 使用 summary.json')
        with open(summary_path) as f:
            summary = json.load(f)

    results, total_fixes, nat_fixes, total_nbs = full_clean(summary)

    with open(summary_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))

    print(f'[CLEAN v5] 完成: {len(results)}个城市修正, 共{total_fixes}个数据点, NBS替代{total_nbs}个率')
    if results:
        results.sort(key=lambda x: -x[1])
        for name, fixes, nbs_count in results[:20]:
            nbs_tag = f' (NBS×{nbs_count})' if nbs_count > 0 else ''
            print(f'  {name}: {fixes}点{nbs_tag}')

    if nat_fixes:
        print(f'[CLEAN v5] 全国均价: {nat_fixes}点修正')

    # Verify: check max MoM
    violations = 0
    for name, city in summary['cities'].items():
        for i in range(1, len(city['prices'])):
            if city['prices'][i - 1] > 0:
                rate = (city['prices'][i] - city['prices'][i - 1]) / city['prices'][i - 1]
                if abs(rate) > 0.025:
                    violations += 1
                    if violations <= 5:
                        print(f'  [WARN] {name} month {i}: {rate*100:.2f}%')

    if violations == 0:
        print(f'[CLEAN v5] 验证通过: 全部城市月环比 ≤ ±2.5%')
    else:
        print(f'[CLEAN v5] {violations}个超限点 (NBS数据允许略超±2%)')

    # Show key city validation
    print('\n[v5] 关键城市校验:')
    for key_city in ['广州', '北京', '上海', '深圳', '西宁', '吉林']:
        if key_city in summary['cities']:
            p = summary['cities'][key_city]['prices']
            if len(p) >= 2 and p[0] > 0 and p[-1] > 0:
                total_change = (p[-1] - p[0]) / p[0] * 100
                print(f'  {key_city}: {p[0]:,} → {p[-1]:,} ({total_change:+.1f}%)')

    # Update bundled JS
    bundled_path = os.path.join(os.path.dirname(DATA_DIR), 'miniprogram', 'data', 'bundled_summary.js')
    if os.path.exists(os.path.dirname(bundled_path)):
        js = 'module.exports = ' + json.dumps(summary, ensure_ascii=False, separators=(',', ':'))
        with open(bundled_path, 'w') as f:
            f.write(js)
        print(f'[CLEAN v5] bundled_summary.js ({len(js) // 1024}KB)')

    print('[CLEAN v5] 完成')


if __name__ == '__main__':
    main()
