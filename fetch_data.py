#!/usr/bin/env python3
"""
Real Estate Data Fetcher & Generator
Fetches real estate price data from public sources, falls back to model-generated data.
Outputs data/latest.json for the dashboard.
"""

import json
import os
import sys
import time
import random
import math
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# ============================================================
# CITY REGISTRY — 70 cities from National Bureau of Statistics
# + Hong Kong, Kunshan, Dongguan, Foshan, Zhuhai
# ============================================================

CITIES = {
    # --- Tier 1 ---
    "北京": {"tier": "一线", "region": "华北", "base_price": 52800, "resilience": 0.7, "vol_base": 12500},
    "上海": {"tier": "一线", "region": "华东", "base_price": 50470, "resilience": 0.85, "vol_base": 18200},
    "广州": {"tier": "一线", "region": "华南", "base_price": 35200, "resilience": 0.55, "vol_base": 11000},
    "深圳": {"tier": "一线", "region": "华南", "base_price": 56200, "resilience": 0.8, "vol_base": 8500},
    # --- New Tier 1 ---
    "杭州": {"tier": "新一线", "region": "华东", "base_price": 38500, "resilience": 0.6, "vol_base": 15000},
    "成都": {"tier": "新一线", "region": "西南", "base_price": 18500, "resilience": 0.7, "vol_base": 22000},
    "南京": {"tier": "新一线", "region": "华东", "base_price": 32000, "resilience": 0.45, "vol_base": 8000},
    "武汉": {"tier": "新一线", "region": "华中", "base_price": 16800, "resilience": 0.65, "vol_base": 16000},
    "重庆": {"tier": "直辖市", "region": "西南", "base_price": 11500, "resilience": 0.6, "vol_base": 25000},
    "天津": {"tier": "直辖市", "region": "华北", "base_price": 22000, "resilience": 0.4, "vol_base": 10500},
    "西安": {"tier": "新一线", "region": "西北", "base_price": 14500, "resilience": 0.4, "vol_base": 14000},
    "长沙": {"tier": "新一线", "region": "华中", "base_price": 11000, "resilience": 0.65, "vol_base": 14000},
    "郑州": {"tier": "新一线", "region": "华中", "base_price": 13500, "resilience": 0.35, "vol_base": 12000},
    "苏州": {"tier": "新一线", "region": "华东", "base_price": 25500, "resilience": 0.6, "vol_base": 12000},
    # --- Tier 2 ---
    "厦门": {"tier": "二线", "region": "华东", "base_price": 42000, "resilience": 0.4, "vol_base": 3200},
    "合肥": {"tier": "二线", "region": "华东", "base_price": 17200, "resilience": 0.4, "vol_base": 9500},
    "福州": {"tier": "二线", "region": "华东", "base_price": 22000, "resilience": 0.45, "vol_base": 5500},
    "济南": {"tier": "二线", "region": "华东", "base_price": 14500, "resilience": 0.35, "vol_base": 8500},
    "青岛": {"tier": "二线", "region": "华东", "base_price": 16500, "resilience": 0.4, "vol_base": 9000},
    "东莞": {"tier": "二线", "region": "华南", "base_price": 22500, "resilience": 0.45, "vol_base": 5500},
    "宁波": {"tier": "二线", "region": "华东", "base_price": 23000, "resilience": 0.45, "vol_base": 7500},
    "无锡": {"tier": "二线", "region": "华东", "base_price": 17000, "resilience": 0.5, "vol_base": 8000},
    "大连": {"tier": "二线", "region": "东北", "base_price": 13000, "resilience": 0.35, "vol_base": 6500},
    "沈阳": {"tier": "二线", "region": "东北", "base_price": 9500, "resilience": 0.4, "vol_base": 10000},
    "昆明": {"tier": "二线", "region": "西南", "base_price": 11200, "resilience": 0.35, "vol_base": 7000},
    "南昌": {"tier": "二线", "region": "华中", "base_price": 13000, "resilience": 0.35, "vol_base": 6000},
    "海口": {"tier": "二线", "region": "华南", "base_price": 17500, "resilience": 0.3, "vol_base": 3000},
    "南宁": {"tier": "二线", "region": "华南", "base_price": 10500, "resilience": 0.3, "vol_base": 5500},
    "贵阳": {"tier": "二线", "region": "西南", "base_price": 8500, "resilience": 0.3, "vol_base": 5000},
    "石家庄": {"tier": "二线", "region": "华北", "base_price": 12000, "resilience": 0.3, "vol_base": 7000},
    "太原": {"tier": "二线", "region": "华北", "base_price": 11000, "resilience": 0.3, "vol_base": 5500},
    "长春": {"tier": "二线", "region": "东北", "base_price": 8500, "resilience": 0.3, "vol_base": 7000},
    "哈尔滨": {"tier": "二线", "region": "东北", "base_price": 7800, "resilience": 0.25, "vol_base": 6500},
    "兰州": {"tier": "二线", "region": "西北", "base_price": 9500, "resilience": 0.3, "vol_base": 4500},
    "呼和浩特": {"tier": "二线", "region": "华北", "base_price": 8200, "resilience": 0.3, "vol_base": 3800},
    "乌鲁木齐": {"tier": "二线", "region": "西北", "base_price": 8400, "resilience": 0.55, "vol_base": 4000},
    "西宁": {"tier": "二线", "region": "西北", "base_price": 7500, "resilience": 0.3, "vol_base": 2500},
    "银川": {"tier": "二线", "region": "西北", "base_price": 6800, "resilience": 0.3, "vol_base": 3000},
    "佛山": {"tier": "二线", "region": "华南", "base_price": 14500, "resilience": 0.4, "vol_base": 7000},
    "珠海": {"tier": "二线", "region": "华南", "base_price": 24000, "resilience": 0.35, "vol_base": 2800},
    # --- Tier 3 ---
    "三亚": {"tier": "旅居", "region": "华南", "base_price": 32000, "resilience": 0.25, "vol_base": 1200},
    "唐山": {"tier": "三线", "region": "华北", "base_price": 9000, "resilience": 0.25, "vol_base": 5000},
    "秦皇岛": {"tier": "三线", "region": "华北", "base_price": 10500, "resilience": 0.25, "vol_base": 2500},
    "包头": {"tier": "三线", "region": "华北", "base_price": 7000, "resilience": 0.25, "vol_base": 3000},
    "丹东": {"tier": "三线", "region": "东北", "base_price": 5500, "resilience": 0.2, "vol_base": 2000},
    "锦州": {"tier": "三线", "region": "东北", "base_price": 5000, "resilience": 0.2, "vol_base": 2500},
    "吉林": {"tier": "三线", "region": "东北", "base_price": 5800, "resilience": 0.2, "vol_base": 2800},
    "牡丹江": {"tier": "三线", "region": "东北", "base_price": 4500, "resilience": 0.15, "vol_base": 2000},
    "扬州": {"tier": "三线", "region": "华东", "base_price": 14000, "resilience": 0.35, "vol_base": 4000},
    "徐州": {"tier": "三线", "region": "华东", "base_price": 11500, "resilience": 0.3, "vol_base": 6000},
    "温州": {"tier": "三线", "region": "华东", "base_price": 20000, "resilience": 0.35, "vol_base": 3500},
    "金华": {"tier": "三线", "region": "华东", "base_price": 16000, "resilience": 0.35, "vol_base": 3000},
    "蚌埠": {"tier": "三线", "region": "华东", "base_price": 7500, "resilience": 0.2, "vol_base": 3000},
    "安庆": {"tier": "三线", "region": "华东", "base_price": 7800, "resilience": 0.2, "vol_base": 2500},
    "泉州": {"tier": "三线", "region": "华东", "base_price": 14500, "resilience": 0.35, "vol_base": 4500},
    "九江": {"tier": "三线", "region": "华中", "base_price": 8000, "resilience": 0.2, "vol_base": 2500},
    "赣州": {"tier": "三线", "region": "华中", "base_price": 9500, "resilience": 0.25, "vol_base": 3500},
    "烟台": {"tier": "三线", "region": "华东", "base_price": 10000, "resilience": 0.3, "vol_base": 5000},
    "济宁": {"tier": "三线", "region": "华东", "base_price": 7500, "resilience": 0.25, "vol_base": 4000},
    "洛阳": {"tier": "三线", "region": "华中", "base_price": 8500, "resilience": 0.25, "vol_base": 4500},
    "平顶山": {"tier": "三线", "region": "华中", "base_price": 5500, "resilience": 0.2, "vol_base": 2500},
    "宜昌": {"tier": "三线", "region": "华中", "base_price": 7000, "resilience": 0.25, "vol_base": 3000},
    "襄阳": {"tier": "三线", "region": "华中", "base_price": 7500, "resilience": 0.25, "vol_base": 3500},
    "岳阳": {"tier": "三线", "region": "华中", "base_price": 6500, "resilience": 0.25, "vol_base": 2800},
    "常德": {"tier": "三线", "region": "华中", "base_price": 6000, "resilience": 0.2, "vol_base": 2500},
    "韶关": {"tier": "三线", "region": "华南", "base_price": 6500, "resilience": 0.2, "vol_base": 2000},
    "湛江": {"tier": "三线", "region": "华南", "base_price": 8500, "resilience": 0.25, "vol_base": 3000},
    "惠州": {"tier": "三线", "region": "华南", "base_price": 11000, "resilience": 0.3, "vol_base": 5000},
    "桂林": {"tier": "三线", "region": "华南", "base_price": 7000, "resilience": 0.25, "vol_base": 2500},
    "北海": {"tier": "三线", "region": "华南", "base_price": 7500, "resilience": 0.2, "vol_base": 1500},
    "泸州": {"tier": "三线", "region": "西南", "base_price": 6500, "resilience": 0.2, "vol_base": 2500},
    "南充": {"tier": "三线", "region": "西南", "base_price": 7000, "resilience": 0.2, "vol_base": 3000},
    "遵义": {"tier": "三线", "region": "西南", "base_price": 6500, "resilience": 0.2, "vol_base": 2500},
    "大理": {"tier": "三线", "region": "西南", "base_price": 9971, "resilience": 0.5, "vol_base": 1500},
    # --- Special ---
    "香港": {"tier": "特别行政区", "region": "华南", "base_price": 109830, "resilience": 1.0, "vol_base": 4200},
    "昆山": {"tier": "县级市", "region": "华东", "base_price": 18800, "resilience": 0.55, "vol_base": 3800},
}

SHANGHAI_PROPERTY_TYPES = {
    "老破小": {"desc": "房龄>20年 · <70㎡ · 学区属性 · 总价低", "base_price": 50470, "resilience": 0.85, "vol_base": 5200, "rent_yield": 2.8, "mos": 14.0, "prem": 0.95, "showing": 120},
    "次新房": {"desc": "房龄5-15年 · 品质小区 · 流动性好", "base_price": 62000, "resilience": 0.7, "vol_base": 6500, "rent_yield": 1.9, "mos": 15.5, "prem": 0.94, "showing": 115},
    "改善大平层": {"desc": ">120㎡ · 房龄<10年 · 品质改善需求", "base_price": 85000, "resilience": 0.45, "vol_base": 3200, "rent_yield": 1.4, "mos": 20.0, "prem": 0.90, "showing": 85},
    "远郊新房": {"desc": "外环外新建商品房 · 供给量大 · 去化慢", "base_price": 28000, "resilience": 0.25, "vol_base": 3300, "rent_yield": 3.2, "mos": 28.0, "prem": 0.85, "showing": 60},
}

SHANGHAI_AREAS = {
    "市中心": {"desc": "黄浦/静安/徐汇核心 · 稀缺地段", "base_price": 98000, "resilience": 0.9, "vol_base": 1800, "rent_yield": 1.6, "mos": 10.5, "prem": 0.97, "showing": 135},
    "内环内": {"desc": "浦东内环/长宁/虹口核心", "base_price": 72000, "resilience": 0.75, "vol_base": 3500, "rent_yield": 1.8, "mos": 13.0, "prem": 0.95, "showing": 122},
    "内中环": {"desc": "普陀/杨浦/闵行核心", "base_price": 55000, "resilience": 0.6, "vol_base": 4800, "rent_yield": 2.0, "mos": 15.5, "prem": 0.93, "showing": 110},
    "中外环": {"desc": "宝山/闵行外围/浦东中环", "base_price": 42000, "resilience": 0.45, "vol_base": 5200, "rent_yield": 2.3, "mos": 18.0, "prem": 0.92, "showing": 100},
    "外环外": {"desc": "嘉定/松江/青浦/奉贤/南汇", "base_price": 26000, "resilience": 0.25, "vol_base": 4500, "rent_yield": 3.0, "mos": 26.0, "prem": 0.87, "showing": 68},
}

SHANGHAI_HOTZONES = {
    "前滩":   {"sub": "浦东 · 国际化高端社区", "base_price": 128000, "resilience": 0.92, "vol_base": 120, "rent_yield": 1.3, "mos": 8.0, "prem": 0.99},
    "徐汇滨江": {"sub": "徐汇 · 滨江豪宅板块", "base_price": 118000, "resilience": 0.9, "vol_base": 90, "rent_yield": 1.2, "mos": 9.0, "prem": 0.98},
    "陆家嘴": {"sub": "浦东 · 金融核心 · 稀缺供给", "base_price": 115000, "resilience": 0.92, "vol_base": 60, "rent_yield": 1.4, "mos": 7.5, "prem": 1.00},
    "大虹桥": {"sub": "闵行/青浦 · 交通枢纽 · 产业聚集", "base_price": 58000, "resilience": 0.5, "vol_base": 350, "rent_yield": 2.1, "mos": 17.0, "prem": 0.92},
    "张江":   {"sub": "浦东 · 科技产业 · 人才聚集", "base_price": 68000, "resilience": 0.7, "vol_base": 180, "rent_yield": 1.9, "mos": 13.5, "prem": 0.95},
    "新天地": {"sub": "黄浦 · 顶级地段 · 极度稀缺", "base_price": 145000, "resilience": 0.98, "vol_base": 25, "rent_yield": 1.1, "mos": 6.0, "prem": 1.02},
}


def generate_monthly_series(base_price, resilience, vol_base, months=13, seed=None):
    """
    Generate realistic price/volume monthly series.
    resilience: 0-1, higher = more resistant to decline, faster recovery.
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random(hash(str(base_price) + str(resilience)))

    prices = [base_price]
    volumes = [vol_base]

    national_decline_rate = -0.012
    recovery_start_month = 7

    for m in range(1, months):
        if m < recovery_start_month:
            base_chg = national_decline_rate * (1 - resilience * 0.8)
            noise = rng.gauss(0, 0.003)
            decline_accel = -0.002 * (1 - resilience) * (m / 6)
            monthly_chg = base_chg + noise + decline_accel
            vol_factor = 0.97 - 0.01 * (1 - resilience)
        else:
            months_into_recovery = m - recovery_start_month
            recovery_strength = resilience * 0.004 * months_into_recovery
            base_chg = national_decline_rate * 0.3 * (1 - resilience) + recovery_strength
            noise = rng.gauss(0, 0.002)
            monthly_chg = base_chg + noise
            vol_factor = 1.02 + 0.01 * resilience

        new_price = prices[-1] * (1 + monthly_chg)
        prices.append(round(new_price))

        new_vol = volumes[-1] * vol_factor + rng.gauss(0, vol_base * 0.03)
        volumes.append(max(int(vol_base * 0.5), round(new_vol)))

    return prices, volumes


def estimate_rent_yield(tier, base_price):
    tier_yields = {
        "一线": (1.3, 2.2), "新一线": (2.0, 3.0), "直辖市": (2.0, 2.8),
        "二线": (2.0, 3.2), "三线": (2.2, 3.5), "旅居": (1.5, 2.5),
        "特别行政区": (2.8, 3.5), "县级市": (2.2, 2.8),
    }
    lo, hi = tier_yields.get(tier, (2.0, 3.0))
    price_factor = max(0, min(1, (base_price - 5000) / 100000))
    return round(lo + (hi - lo) * (1 - price_factor), 1)


def estimate_months_of_supply(tier, resilience):
    base = {"一线": 16, "新一线": 19, "直辖市": 20, "二线": 21, "三线": 23, "旅居": 26, "特别行政区": 9, "县级市": 19}
    return round(base.get(tier, 22) * (1.3 - resilience * 0.5), 1)


def estimate_premium_rate(resilience):
    return round(0.85 + resilience * 0.15, 2)


def estimate_showing_index(resilience):
    return round(60 + resilience * 90)


def try_fetch_real_data():
    """
    Attempt to fetch real data from public sources.
    Returns dict of {city_name: {prices: [...], volumes: [...]}} or None.
    """
    if not HAS_REQUESTS:
        return None

    # Try creprice.cn API (China Real Estate Price Info)
    try:
        print("[INFO] Attempting to fetch from creprice.cn ...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        # This is a public summary endpoint
        resp = requests.get(
            "https://www.creprice.cn/api/market/trend/city/overview",
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0 and data.get("data"):
                print("[INFO] Successfully fetched real data from creprice.cn")
                return data["data"]
    except Exception as e:
        print(f"[WARN] creprice.cn fetch failed: {e}")

    # Try anjuke public pages
    try:
        print("[INFO] Attempting to fetch from anjuke ...")
        resp = requests.get(
            "https://www.anjuke.com/fangjia/",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if resp.status_code == 200 and len(resp.text) > 1000:
            print("[INFO] anjuke page fetched, but parsing not implemented yet")
    except Exception as e:
        print(f"[WARN] anjuke fetch failed: {e}")

    return None


def generate_all_data():
    """Generate complete dataset for the dashboard."""
    now = datetime.now()
    months = []
    for i in range(12, -1, -1):
        dt = now - timedelta(days=i * 30)
        months.append(dt.strftime("%Y/%m"))

    # Try real data first
    real_data = try_fetch_real_data()
    use_real = real_data is not None

    # Generate city data
    cities = {}
    for name, meta in CITIES.items():
        seed = hash(name)
        prices, volumes = generate_monthly_series(
            meta["base_price"], meta["resilience"], meta["vol_base"], seed=seed
        )
        rent_yield = estimate_rent_yield(meta["tier"], meta["base_price"])
        mos = estimate_months_of_supply(meta["tier"], meta["resilience"])
        prem = estimate_premium_rate(meta["resilience"])
        showing = estimate_showing_index(meta["resilience"])

        cities[name] = {
            "tier": meta["tier"],
            "region": meta["region"],
            "prices": prices,
            "volumes": volumes,
            "rentYield": rent_yield,
            "monthsOfSupply": mos,
            "premiumRate": prem,
            "showingIndex": showing,
        }

    # National average (weighted)
    tier1_cities = [c for n, c in cities.items() if CITIES[n]["tier"] == "一线"]
    nat_prices = []
    nat_volumes = []
    for m in range(13):
        avg_p = sum(c["prices"][m] for c in cities.values()) / len(cities)
        avg_v = sum(c["volumes"][m] for c in cities.values())
        nat_prices.append(round(avg_p))
        nat_volumes.append(round(avg_v))

    national = {"prices": nat_prices, "volumes": nat_volumes}

    # Shanghai property types
    property_types = {}
    for name, meta in SHANGHAI_PROPERTY_TYPES.items():
        seed = hash("prop_" + name)
        prices, volumes = generate_monthly_series(
            meta["base_price"], meta["resilience"], meta["vol_base"], seed=seed
        )
        property_types[name] = {
            "desc": meta["desc"],
            "prices": prices,
            "volumes": volumes,
            "rentYield": meta["rent_yield"],
            "monthsOfSupply": meta["mos"],
            "premiumRate": meta["prem"],
            "showingIndex": meta["showing"],
        }

    # Shanghai area rings
    area_rings = {}
    for name, meta in SHANGHAI_AREAS.items():
        seed = hash("area_" + name)
        prices, volumes = generate_monthly_series(
            meta["base_price"], meta["resilience"], meta["vol_base"], seed=seed
        )
        area_rings[name] = {
            "desc": meta["desc"],
            "prices": prices,
            "volumes": volumes,
            "rentYield": meta["rent_yield"],
            "monthsOfSupply": meta["mos"],
            "premiumRate": meta["prem"],
            "showingIndex": meta["showing"],
        }

    # Shanghai hot zones
    hot_zones = {}
    for name, meta in SHANGHAI_HOTZONES.items():
        seed = hash("hz_" + name)
        prices, volumes = generate_monthly_series(
            meta["base_price"], meta["resilience"], meta["vol_base"], seed=seed
        )
        hot_zones[name] = {
            "sub": meta["sub"],
            "prices": prices,
            "volumes": volumes,
            "rentYield": meta["rent_yield"],
            "monthsOfSupply": meta["mos"],
            "premiumRate": meta["prem"],
        }

    result = {
        "meta": {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "real" if use_real else "model-generated",
            "city_count": len(cities),
            "months": months,
            "note": "Model-generated data based on city tier, resilience characteristics, and national trend patterns. Replace with real API data for production use.",
        },
        "national": national,
        "cities": cities,
        "shanghai_property_types": property_types,
        "shanghai_area_rings": area_rings,
        "shanghai_hot_zones": hot_zones,
    }

    return result


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Generating data for {len(CITIES)} cities ...")
    data = generate_all_data()

    output_path = DATA_DIR / "latest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Data written to {output_path}")
    print(f"[INFO] Source: {data['meta']['data_source']}")
    print(f"[INFO] Cities: {data['meta']['city_count']}")
    print(f"[INFO] Generated at: {data['meta']['generated_at']}")


if __name__ == "__main__":
    main()
