"""
smooth_prices.py — 对已合并的价格数据做平滑处理
检测脉冲型跳变（涨了立刻跌回来），用前后稳定值线性插值替代
直接处理 data/summary.json 和 data/city/*.json，无需重新爬虫
"""
import json
import os
import copy

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
PULSE_THRESHOLD = 0.04
SINGLE_THRESHOLD = 0.15

def find_anomalies(prices):
    """找出所有异常月份的索引"""
    if not prices or len(prices) < 3:
        return set()

    bad = set()

    for i in range(1, len(prices) - 1):
        chg1 = (prices[i] - prices[i-1]) / prices[i-1]
        chg2 = (prices[i+1] - prices[i]) / prices[i]
        # 脉冲: 方向相反且两侧都超阈值
        if chg1 * chg2 < 0 and abs(chg1) > PULSE_THRESHOLD and abs(chg2) > PULSE_THRESHOLD:
            bad.add(i)

    for i in range(1, len(prices)):
        chg = abs((prices[i] - prices[i-1]) / prices[i-1])
        if chg > SINGLE_THRESHOLD:
            bad.add(i)

    return bad


def smooth(prices):
    """对异常月份做线性插值平滑"""
    if not prices or len(prices) < 3:
        return prices, 0

    result = list(prices)
    bad = find_anomalies(result)
    if not bad:
        return result, 0

    # 扩展连续异常区间
    # 例如 衢州 index 1,6,7,...,13 都有问题，需要找到稳定的锚点
    fixed = 0

    # 迭代处理，因为修一个点可能影响相邻检测
    for _round in range(3):
        bad = find_anomalies(result)
        if not bad:
            break

        for i in sorted(bad):
            # 找左侧最近的稳定点
            left = i - 1
            while left in bad and left > 0:
                left -= 1
            # 找右侧最近的稳定点
            right = i + 1
            while right in bad and right < len(result) - 1:
                right += 1

            if left not in bad and right not in bad and right > left:
                # 对 left+1 到 right-1 之间的所有点做线性插值
                for j in range(left + 1, right):
                    ratio = (j - left) / (right - left)
                    result[j] = round(result[left] + (result[right] - result[left]) * ratio)
                    fixed += 1

    return result, fixed


def main():
    # 处理 summary.json
    summary_path = os.path.join(DATA_DIR, 'summary.json')
    with open(summary_path) as f:
        summary = json.load(f)

    total_fixed = 0
    affected_cities = []

    for name, city in summary['cities'].items():
        original = list(city['prices'])
        smoothed, count = smooth(city['prices'])
        if count > 0:
            city['prices'] = smoothed
            affected_cities.append((name, count, original, smoothed))
            total_fixed += count

    # 重算 national (全国均价)
    all_prices = [c['prices'] for c in summary['cities'].values()]
    n_months = len(summary['meta']['months'])
    nat_prices = []
    for m in range(n_months):
        vals = [p[m] for p in all_prices if m < len(p)]
        nat_prices.append(round(sum(vals) / len(vals)))
    summary['national']['prices'] = nat_prices

    # 写回 summary.json
    with open(summary_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))

    # 处理 city/*.json
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

    # 报告
    months = summary['meta']['months']
    print(f'平滑完成: {len(affected_cities)}个城市, 共{total_fixed}个数据点被修正')
    print()
    for name, count, orig, smoothed in affected_cities:
        diffs = []
        for i in range(len(orig)):
            if orig[i] != smoothed[i]:
                m = months[i] if i < len(months) else f'[{i}]'
                diffs.append(f'{m}: {orig[i]}→{smoothed[i]}')
        print(f'  {name} ({count}点): {", ".join(diffs)}')

    print(f'\n文件已更新: summary.json + {len(city_files)}个城市文件')


if __name__ == '__main__':
    main()
