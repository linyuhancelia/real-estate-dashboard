#!/usr/bin/env python3
"""
patch_crawl.py — 针对数据源切换月份有跳变的城市进行补爬
只重爬有问题的城市, 用链式指数法重新合并, 更新数据文件
"""
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')

sys.path.insert(0, SCRIPT_DIR)

SWITCH_MONTHS = {'2024/08', '2025/08', '2026/01', '2026/02', '2026/03', '2026/04'}
JUMP_THRESHOLD = 0.03


def find_cities_to_patch(summary):
    """找出在切换月份有显著跳变的城市"""
    months = summary['meta']['months']
    switch_indices = {i for i, m in enumerate(months) if m in SWITCH_MONTHS}

    to_patch = []
    for name, city in summary['cities'].items():
        p = city['prices']
        jump_months = []
        for i in switch_indices:
            if i > 0 and i < len(p) and p[i - 1] > 0:
                chg = abs((p[i] - p[i - 1]) / p[i - 1])
                if chg > JUMP_THRESHOLD:
                    jump_months.append((months[i], round(chg * 100, 1)))
        if jump_months:
            to_patch.append((name, jump_months))

    return to_patch


def main():
    from fetch_data import (
        AnjukeCrawler, CrepriceCrawler, FangCrawler,
        CITY_CODES, FANG_CITY_CODES, TARGET_CITIES,
        merge_monthly_prices, interpolate_monthly,
        estimate_volumes
    )

    summary_path = os.path.join(DATA_DIR, 'summary.json')
    with open(summary_path) as f:
        summary = json.load(f)

    to_patch = find_cities_to_patch(summary)
    if not to_patch:
        print('[PATCH] 无需补爬, 所有城市数据正常')
        return

    print(f'[PATCH] 需补爬 {len(to_patch)} 个城市:')
    for name, jms in to_patch:
        print(f'  {name}: {jms}')
    print()

    NUM_MONTHS = len(summary['meta']['months'])

    anjuke = AnjukeCrawler()
    creprice = CrepriceCrawler()
    fang = FangCrawler()

    raw_dir = os.path.join(DATA_DIR, 'raw_sources')
    os.makedirs(raw_dir, exist_ok=True)

    patched = 0
    failed = 0

    for name, jump_info in to_patch:
        print(f'[{patched + failed + 1}/{len(to_patch)}] 补爬 {name}...', end=' ', flush=True)

        try:
            raw_prices = anjuke.fetch_city_prices(name)
            anjuke._delay()

            cp_code = CITY_CODES.get(name)
            cp_prices = {}
            if cp_code:
                cp_prices = creprice.fetch_city_prices(cp_code)
                creprice._delay()

            fang_code = FANG_CITY_CODES.get(name)
            fang_prices = {}
            if fang_code:
                fang_prices = fang.fetch_city_prices(fang_code)
                fang._delay()

            sources = []
            if raw_prices:
                sources.append(f'安居客{len(raw_prices)}')
            if cp_prices:
                sources.append(f'房价行情{len(cp_prices)}')
            if fang_prices:
                sources.append(f'房天下{len(fang_prices)}')

            if not raw_prices and not cp_prices and not fang_prices:
                print('✗ 无数据')
                failed += 1
                continue

            # 保存原始数据
            raw_record = {
                'anjuke': raw_prices,
                'creprice': cp_prices,
                'fang': fang_prices,
                'crawl_date': time.strftime('%Y-%m-%d %H:%M'),
                'patch': True,
            }
            city_files = summary['meta'].get('city_files', {})
            code = city_files.get(name, name)
            raw_path = os.path.join(raw_dir, f'{code}.json')
            with open(raw_path, 'w') as f:
                json.dump(raw_record, f, ensure_ascii=False, separators=(',', ':'))

            # 链式融合
            if raw_prices:
                new_prices, _ = merge_monthly_prices(
                    raw_prices, cp_prices, fang_prices, NUM_MONTHS)
            elif cp_prices:
                new_prices, _ = merge_monthly_prices(
                    cp_prices, fang_prices, None, NUM_MONTHS)
            else:
                new_prices, _ = interpolate_monthly(fang_prices, NUM_MONTHS)

            if not new_prices or all(p == 0 for p in new_prices):
                print('✗ 融合失败')
                failed += 1
                continue

            # 对比新旧数据
            old_prices = summary['cities'][name]['prices']
            diffs = []
            months = summary['meta']['months']
            for i in range(min(len(old_prices), len(new_prices))):
                if old_prices[i] != new_prices[i]:
                    chg = round((new_prices[i] - old_prices[i]) / old_prices[i] * 100, 1)
                    diffs.append(f'{months[i]}:{chg:+.1f}%')

            # 检查新数据的最大环比跳变
            new_max_mom = 0
            for i in range(1, len(new_prices)):
                if new_prices[i - 1] > 0:
                    mom = abs((new_prices[i] - new_prices[i - 1]) / new_prices[i - 1])
                    new_max_mom = max(new_max_mom, mom)

            old_max_mom = 0
            for i in range(1, len(old_prices)):
                if old_prices[i - 1] > 0:
                    mom = abs((old_prices[i] - old_prices[i - 1]) / old_prices[i - 1])
                    old_max_mom = max(old_max_mom, mom)

            tier = TARGET_CITIES.get(name, {}).get('tier', '三线')
            new_volumes = estimate_volumes(new_prices, tier, base_seed=hash(name))

            # 更新 summary
            summary['cities'][name]['prices'] = new_prices
            summary['cities'][name]['volumes'] = new_volumes

            # 更新 city/*.json
            city_path = os.path.join(DATA_DIR, 'city', f'{code}.json')
            if os.path.exists(city_path):
                with open(city_path) as f:
                    detail = json.load(f)
                detail['prices'] = new_prices
                detail['volumes'] = new_volumes
                with open(city_path, 'w') as f:
                    json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))

            src_str = '+'.join(sources)
            print(f'✓ {src_str} | maxMoM: {old_max_mom*100:.1f}%→{new_max_mom*100:.1f}% | {len(diffs)}点变化')
            patched += 1

        except Exception as e:
            print(f'✗ 异常: {e}')
            failed += 1

    # 重算全国均价
    all_prices = [c['prices'] for c in summary['cities'].values()]
    n_months = len(summary['meta']['months'])
    nat_prices = []
    for m in range(n_months):
        vals = [p[m] for p in all_prices if m < len(p)]
        nat_prices.append(round(sum(vals) / len(vals)))
    summary['national']['prices'] = nat_prices

    # 写回 summary
    with open(summary_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))

    # 平滑安全网
    print(f'\n[PATCH] 补爬完成: {patched}成功, {failed}失败')
    print('[PATCH] 运行平滑安全网...')

    from smooth_prices import smooth
    months = summary['meta']['months']
    smooth_count = 0
    for name, city in summary['cities'].items():
        smoothed, count = smooth(city['prices'], months)
        if count > 0:
            city['prices'] = smoothed
            smooth_count += count
            code = summary['meta'].get('city_files', {}).get(name, name)
            city_path = os.path.join(DATA_DIR, 'city', f'{code}.json')
            if os.path.exists(city_path):
                with open(city_path) as f:
                    detail = json.load(f)
                detail['prices'] = city['prices']
                with open(city_path, 'w') as f:
                    json.dump(detail, f, ensure_ascii=False, separators=(',', ':'))

    if smooth_count:
        # 重算全国均价
        all_prices = [c['prices'] for c in summary['cities'].values()]
        nat_prices = []
        for m in range(n_months):
            vals = [p[m] for p in all_prices if m < len(p)]
            nat_prices.append(round(sum(vals) / len(vals)))
        summary['national']['prices'] = nat_prices
        with open(summary_path, 'w') as f:
            json.dump(summary, f, ensure_ascii=False, separators=(',', ':'))
        print(f'[SMOOTH] 额外平滑 {smooth_count} 个数据点')

    # 更新 bundled_summary.js
    bundled_path = os.path.join(PROJECT_DIR, 'miniprogram', 'data', 'bundled_summary.js')
    if os.path.exists(os.path.dirname(bundled_path)):
        js = 'module.exports = ' + json.dumps(summary, ensure_ascii=False, separators=(',', ':'))
        with open(bundled_path, 'w') as f:
            f.write(js)
        print(f'[PATCH] bundled_summary.js 已更新 ({len(js)//1024}KB)')

    print('[PATCH] 全部完成')


if __name__ == '__main__':
    main()
