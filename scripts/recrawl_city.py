#!/usr/bin/env python3
"""Re-crawl board-level data for a single city and update its city JSON file."""
import json, os, re, sys, time, random, requests

FANG_MOBILE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

FANG_CITY_CODES = {
    '上海': 'sh', '北京': 'bj', '深圳': 'sz', '广州': 'gz',
    '杭州': 'hz', '南京': 'nanjing', '武汉': 'wuhan', '成都': 'cd',
    '重庆': 'cq', '天津': 'tj', '苏州': 'suzhou', '西安': 'xa',
    '郑州': 'zhengzhou', '长沙': 'cs',
}

def discover_boards(city_code):
    for attempt in range(5):
        try:
            s = requests.Session()
            s.headers.update(FANG_MOBILE_HEADERS)
            if attempt > 0:
                wait = 3 + attempt * 2
                print(f"  重试 {attempt}/4, 等待{wait}s...")
                time.sleep(wait)

            url = f'https://m.fang.com/fangjia/{city_code}/cityhouseprice.html'
            print(f"  请求 cityhouseprice.html ...")
            r = s.get(url, timeout=20)
            print(f"  状态码: {r.status_code}, 页面长度: {len(r.text)}")

            if r.status_code != 200 or len(r.text) < 5000:
                print(f"  页面异常，重试...")
                continue

            ep_match = re.search(r"echartsPriceData\s*=\s*'(\[.*?\])'", r.text, re.DOTALL)
            if not ep_match:
                print(f"  未找到 echartsPriceData，重试...")
                continue

            raw_ep = ep_match.group(1)
            print(f"  echartsPriceData 长度: {len(raw_ep)}")
            try:
                ep_data = json.loads(raw_ep)
            except json.JSONDecodeError as e:
                print(f"  JSON解析失败: {e}")
                print(f"  前100字符: {repr(raw_ep[:100])}")
                continue
            dist_ids = []
            for d in ep_data:
                if isinstance(d, str):
                    if not d.strip():
                        continue
                    d = json.loads(d)
                did = d.get('districtId')
                dname = d.get('districtName', '')
                if did:
                    dist_ids.append((str(did), dname))

            print(f"  找到 {len(dist_ids)} 个区: {[n for _,n in dist_ids]}")

            if not dist_ids:
                continue

            for did, dname in dist_ids[:5]:
                time.sleep(2)
                print(f"  尝试区 {dname}({did}) 获取 areaInfo...")
                r2 = s.get(f'https://m.fang.com/fangjia/{city_code}_list_{did}/', timeout=20)
                if r2.status_code != 200 or len(r2.text) < 5000:
                    print(f"    状态码: {r2.status_code}, 长度: {len(r2.text)}, 跳过")
                    continue

                match = re.search(r"pageConfig\.areaInfo\s*=\s*'(\{.+?\})'\s*;", r2.text, re.DOTALL)
                if not match:
                    match = re.search(r'pageConfig\.areaInfo\s*=\s*"(\{.+?\})"\s*;', r2.text, re.DOTALL)
                if not match:
                    match = re.search(r"pageConfig\.areaInfo\s*=\s*(\{.+?\})\s*;\s*pageConfig", r2.text, re.DOTALL)
                if not match:
                    print(f"    未找到 areaInfo, 跳过")
                    continue

                raw = match.group(1)
                info = json.loads(raw)
                result = {}
                total_boards = 0
                for dist_name, dist_data in info.items():
                    if not isinstance(dist_data, dict):
                        continue
                    dist_id = dist_data.get('id') or dist_data.get('districtId')
                    boards = []
                    commerce = dist_data.get('comerce') or dist_data.get('commerce') or []
                    for b in commerce:
                        if isinstance(b, dict):
                            bid = b.get('id') or b.get('areaId')
                            bname = b.get('comareaName') or b.get('name') or b.get('areaName', '')
                            if bid and bname:
                                boards.append({'id': str(bid), 'name': bname})
                    if dist_id and boards:
                        result[dist_name] = {'id': str(dist_id), 'boards': boards}
                        total_boards += len(boards)

                if result:
                    print(f"  ✓ areaInfo 发现 {len(result)} 个区, {total_boards} 个板块")
                    return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")
    return {}


def fetch_board_prices(city_code, district_id, board_id, session):
    try:
        url = f'https://m.fang.com/fangjia/{city_code}_list_{district_id}_{board_id}/'
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return {}
        for var_name in ['areaChartData3', 'areaChartData1', 'areaChartData']:
            match = re.search(
                rf"pageConfig\.{var_name}\s*=\s*(\{{.*?\}})\s*;", r.text, re.DOTALL)
            if match:
                raw = match.group(1)
                raw = re.sub(r"'", '"', raw)
                data = json.loads(raw)
                x = data.get('x', [])
                y1 = data.get('y1', [])
                if x and y1:
                    prices = {}
                    for month_label, price in zip(x, y1):
                        if price and price > 0:
                            parts = month_label.split('-')
                            if len(parts) == 2:
                                key = f"20{parts[0]}/{parts[1]}"
                                prices[key] = int(price)
                    if prices:
                        return prices
        return {}
    except Exception as e:
        return {}


def build_board_hot_zones(board_data, city_prices):
    rng = random.Random(42)
    avg_price = city_prices[-1] if city_prices else 10000
    result = {}
    for board_name, binfo in board_data.items():
        district = binfo.get('district', '')
        monthly_prices = binfo.get('prices', {})
        if not monthly_prices:
            continue
        sorted_months = sorted(monthly_prices.keys())
        price_list = [monthly_prices[m] for m in sorted_months]
        vol_list = [max(5, round(50 * (monthly_prices[m] / avg_price) *
                    (1 + rng.gauss(0, 0.08)))) for m in sorted_months]
        latest = price_list[-1] if price_list else avg_price
        ratio = latest / avg_price if avg_price > 0 else 1.0
        result[board_name] = {
            "sub": f"{district}·{board_name}" if district else board_name,
            "district": district,
            "prices": price_list,
            "months": sorted_months,
            "volumes": vol_list,
            "rentYield": round(1.5 + (1 - ratio) * 1.5, 1),
            "monthsOfSupply": round(12 * (2 - ratio), 1),
            "premiumRate": round(0.87 + ratio * 0.08, 2),
        }
    return result


def main():
    city_name = sys.argv[1] if len(sys.argv) > 1 else '上海'
    city_code = FANG_CITY_CODES.get(city_name)
    if not city_code:
        print(f"未知城市: {city_name}")
        sys.exit(1)

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    city_file = os.path.join(data_dir, 'city', f'{city_code}.json')

    if not os.path.exists(city_file):
        print(f"城市文件不存在: {city_file}")
        sys.exit(1)

    with open(city_file, 'r', encoding='utf-8') as f:
        city_data = json.load(f)

    summary_file = os.path.join(data_dir, 'summary.json')
    city_prices = []
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        if city_name in summary.get('cities', {}):
            city_prices = summary['cities'][city_name].get('prices', [])

    print(f"=== 重新爬取 {city_name}({city_code}) 板块数据 ===")
    print(f"当前 hot_zones: {len(city_data.get('hot_zones', {}))} 个")

    print(f"\n[1/3] 发现板块映射...")
    boards_map = discover_boards(city_code)

    if not boards_map:
        print("✗ 无法发现板块映射，退出")
        sys.exit(1)

    total_boards = sum(len(d['boards']) for d in boards_map.values())
    print(f"\n[2/3] 爬取板块价格数据 (共{total_boards}个板块)...")

    board_cap = 200
    board_data = {}
    count = 0
    s = requests.Session()
    s.headers.update(FANG_MOBILE_HEADERS)

    for dist_name, dist_info in boards_map.items():
        dist_id = dist_info['id']
        for board in dist_info['boards']:
            if count >= board_cap:
                print(f"\n  达到上限 {board_cap}，停止")
                break

            bid = board['id']
            bname = board['name']
            count += 1

            delay = random.uniform(0.3, 0.8)
            time.sleep(delay)

            prices = fetch_board_prices(city_code, dist_id, bid, s)
            if prices:
                board_data[bname] = {
                    'district': dist_name,
                    'prices': prices,
                }
                latest = list(prices.values())[-1]
                status = '✓'
            else:
                status = '✗'
                latest = 0

            print(f"  [{count}/{min(total_boards, board_cap)}] {dist_name}/{bname}: {status} {f'{latest}元/㎡' if latest else '无数据'}")

        if count >= board_cap:
            break

    if not board_data:
        print("✗ 未获取到任何板块数据，退出")
        sys.exit(1)

    print(f"\n[3/3] 构建 hot_zones 并保存...")
    hot_zones = build_board_hot_zones(board_data, city_prices)

    city_data['hot_zones'] = hot_zones

    with open(city_file, 'w', encoding='utf-8') as f:
        json.dump(city_data, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(city_file) / 1024
    print(f"\n=== 完成 ===")
    print(f"  板块数: {len(hot_zones)}")
    print(f"  文件大小: {size_kb:.1f}KB")

    top5 = sorted(hot_zones.items(), key=lambda x: x[1]['prices'][-1], reverse=True)[:5]
    print(f"  均价TOP5:")
    for name, v in top5:
        print(f"    {v['district']}/{name}: {v['prices'][-1]}元/㎡")


if __name__ == '__main__':
    main()
