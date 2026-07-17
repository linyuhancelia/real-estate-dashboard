#!/usr/bin/env python3
"""Real Estate Data Crawler v5.1 — 多源数据版
数据来源：
- 安居客(anjuke.com) 城市二手房均价（真实爬取，8-12月）
- 中国房价行情(creprice.cn) 月度均价+区域+板块（真实爬取，全年12月）
- 成交量：基于价格趋势和城市规模的估算模型
- 物业类型：基于城市均价的结构化拆分模型
"""
import json, re, time, random, math, sys, traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[ERROR] 需要安装依赖: pip install requests beautifulsoup4")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"

# ===== 爬虫配置 =====
ANJUKE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                  'Version/16.0 Mobile/15E148 Safari/604.1'
}
ANJUKE_BASE = 'https://mobile.anjuke.com/fangjia'

CREPRICE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json,text/javascript,*/*;q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
}
CREPRICE_BASE = 'https://www.creprice.cn'

REQ_DELAY = (0.3, 0.8)

# ===== 目标城市 =====
TARGET_CITIES = {
    "北京": {"tier": "一线", "province": "北京市"},
    "上海": {"tier": "一线", "province": "上海市"},
    "广州": {"tier": "一线", "province": "广东省"},
    "深圳": {"tier": "一线", "province": "广东省"},
    "杭州": {"tier": "新一线", "province": "浙江省"},
    "成都": {"tier": "新一线", "province": "四川省"},
    "南京": {"tier": "新一线", "province": "江苏省"},
    "武汉": {"tier": "新一线", "province": "湖北省"},
    "重庆": {"tier": "新一线", "province": "重庆市"},
    "天津": {"tier": "新一线", "province": "天津市"},
    "西安": {"tier": "新一线", "province": "陕西省"},
    "长沙": {"tier": "新一线", "province": "湖南省"},
    "郑州": {"tier": "新一线", "province": "河南省"},
    "苏州": {"tier": "新一线", "province": "江苏省"},
    "厦门": {"tier": "二线", "province": "福建省"},
    "合肥": {"tier": "二线", "province": "安徽省"},
    "福州": {"tier": "二线", "province": "福建省"},
    "济南": {"tier": "二线", "province": "山东省"},
    "青岛": {"tier": "二线", "province": "山东省"},
    "东莞": {"tier": "二线", "province": "广东省"},
    "宁波": {"tier": "二线", "province": "浙江省"},
    "无锡": {"tier": "二线", "province": "江苏省"},
    "大连": {"tier": "二线", "province": "辽宁省"},
    "沈阳": {"tier": "二线", "province": "辽宁省"},
    "昆明": {"tier": "二线", "province": "云南省"},
    "南昌": {"tier": "二线", "province": "江西省"},
    "海口": {"tier": "二线", "province": "海南省"},
    "南宁": {"tier": "二线", "province": "广西壮族自治区"},
    "贵阳": {"tier": "二线", "province": "贵州省"},
    "石家庄": {"tier": "二线", "province": "河北省"},
    "太原": {"tier": "二线", "province": "山西省"},
    "长春": {"tier": "二线", "province": "吉林省"},
    "哈尔滨": {"tier": "二线", "province": "黑龙江省"},
    "兰州": {"tier": "二线", "province": "甘肃省"},
    "呼和浩特": {"tier": "二线", "province": "内蒙古自治区"},
    "乌鲁木齐": {"tier": "二线", "province": "新疆维吾尔自治区"},
    "西宁": {"tier": "二线", "province": "青海省"},
    "银川": {"tier": "二线", "province": "宁夏回族自治区"},
    "佛山": {"tier": "二线", "province": "广东省"},
    "珠海": {"tier": "二线", "province": "广东省"},
    "常州": {"tier": "二线", "province": "江苏省"},
    "南通": {"tier": "二线", "province": "江苏省"},
    "嘉兴": {"tier": "二线", "province": "浙江省"},
    "中山": {"tier": "二线", "province": "广东省"},
    "芜湖": {"tier": "二线", "province": "安徽省"},
    "唐山": {"tier": "三线", "province": "河北省"},
    "秦皇岛": {"tier": "三线", "province": "河北省"},
    "保定": {"tier": "三线", "province": "河北省"},
    "邯郸": {"tier": "三线", "province": "河北省"},
    "廊坊": {"tier": "三线", "province": "河北省"},
    "包头": {"tier": "三线", "province": "内蒙古自治区"},
    "丹东": {"tier": "三线", "province": "辽宁省"},
    "锦州": {"tier": "三线", "province": "辽宁省"},
    "鞍山": {"tier": "三线", "province": "辽宁省"},
    "吉林": {"tier": "三线", "province": "吉林省"},
    "牡丹江": {"tier": "三线", "province": "黑龙江省"},
    "扬州": {"tier": "三线", "province": "江苏省"},
    "徐州": {"tier": "三线", "province": "江苏省"},
    "连云港": {"tier": "三线", "province": "江苏省"},
    "淮安": {"tier": "三线", "province": "江苏省"},
    "盐城": {"tier": "三线", "province": "江苏省"},
    "镇江": {"tier": "三线", "province": "江苏省"},
    "泰州": {"tier": "三线", "province": "江苏省"},
    "宿迁": {"tier": "三线", "province": "江苏省"},
    "温州": {"tier": "三线", "province": "浙江省"},
    "金华": {"tier": "三线", "province": "浙江省"},
    "绍兴": {"tier": "三线", "province": "浙江省"},
    "台州": {"tier": "三线", "province": "浙江省"},
    "湖州": {"tier": "三线", "province": "浙江省"},
    "衢州": {"tier": "三线", "province": "浙江省"},
    "丽水": {"tier": "三线", "province": "浙江省"},
    "蚌埠": {"tier": "三线", "province": "安徽省"},
    "安庆": {"tier": "三线", "province": "安徽省"},
    "马鞍山": {"tier": "三线", "province": "安徽省"},
    "泉州": {"tier": "三线", "province": "福建省"},
    "漳州": {"tier": "三线", "province": "福建省"},
    "莆田": {"tier": "三线", "province": "福建省"},
    "龙岩": {"tier": "三线", "province": "福建省"},
    "九江": {"tier": "三线", "province": "江西省"},
    "赣州": {"tier": "三线", "province": "江西省"},
    "上饶": {"tier": "三线", "province": "江西省"},
    "烟台": {"tier": "三线", "province": "山东省"},
    "济宁": {"tier": "三线", "province": "山东省"},
    "潍坊": {"tier": "三线", "province": "山东省"},
    "临沂": {"tier": "三线", "province": "山东省"},
    "淄博": {"tier": "三线", "province": "山东省"},
    "泰安": {"tier": "三线", "province": "山东省"},
    "洛阳": {"tier": "三线", "province": "河南省"},
    "平顶山": {"tier": "三线", "province": "河南省"},
    "南阳": {"tier": "三线", "province": "河南省"},
    "新乡": {"tier": "三线", "province": "河南省"},
    "宜昌": {"tier": "三线", "province": "湖北省"},
    "襄阳": {"tier": "三线", "province": "湖北省"},
    "荆州": {"tier": "三线", "province": "湖北省"},
    "岳阳": {"tier": "三线", "province": "湖南省"},
    "常德": {"tier": "三线", "province": "湖南省"},
    "株洲": {"tier": "三线", "province": "湖南省"},
    "衡阳": {"tier": "三线", "province": "湖南省"},
    "韶关": {"tier": "三线", "province": "广东省"},
    "湛江": {"tier": "三线", "province": "广东省"},
    "惠州": {"tier": "三线", "province": "广东省"},
    "江门": {"tier": "三线", "province": "广东省"},
    "汕头": {"tier": "三线", "province": "广东省"},
    "肇庆": {"tier": "三线", "province": "广东省"},
    "茂名": {"tier": "三线", "province": "广东省"},
    "清远": {"tier": "三线", "province": "广东省"},
    "潮州": {"tier": "三线", "province": "广东省"},
    "桂林": {"tier": "三线", "province": "广西壮族自治区"},
    "柳州": {"tier": "三线", "province": "广西壮族自治区"},
    "泸州": {"tier": "三线", "province": "四川省"},
    "南充": {"tier": "三线", "province": "四川省"},
    "绵阳": {"tier": "三线", "province": "四川省"},
    "德阳": {"tier": "三线", "province": "四川省"},
    "遵义": {"tier": "三线", "province": "贵州省"},
    "曲靖": {"tier": "三线", "province": "云南省"},
    "宝鸡": {"tier": "三线", "province": "陕西省"},
    "昆山": {"tier": "三线", "province": "江苏省"},
    "三亚": {"tier": "旅居", "province": "海南省"},
    "大理": {"tier": "旅居", "province": "云南省"},
    "北海": {"tier": "旅居", "province": "广西壮族自治区"},
    "丽江": {"tier": "旅居", "province": "云南省"},
    "西双版纳": {"tier": "旅居", "province": "云南省"},
    "舟山": {"tier": "旅居", "province": "浙江省"},
    "威海": {"tier": "旅居", "province": "山东省"},
    "香港": {"tier": "特别行政区", "province": "香港特别行政区"},
}

# ===== creprice.cn 城市代码映射 =====
CITY_CODES = {
    "北京": "bj", "上海": "sh", "广州": "gz", "深圳": "sz",
    "杭州": "hz", "成都": "cd", "南京": "nj", "武汉": "wh",
    "重庆": "cq", "天津": "tj", "西安": "xa", "长沙": "cs",
    "郑州": "zz", "苏州": "su",
    "厦门": "xm", "合肥": "hf", "福州": "fz", "济南": "jn",
    "青岛": "qd", "东莞": "dg", "宁波": "nb", "无锡": "wx",
    "大连": "dl", "沈阳": "sy", "昆明": "km", "南昌": "nc",
    "海口": "haikou", "南宁": "nn", "贵阳": "gy", "石家庄": "sjz",
    "太原": "ty", "长春": "cc", "哈尔滨": "hrb", "兰州": "lz",
    "呼和浩特": "hhht", "乌鲁木齐": "wlmq", "西宁": "xn",
    "银川": "yinchuan", "佛山": "fs", "珠海": "zh", "常州": "changzhou",
    "南通": "nt", "嘉兴": "jx", "中山": "zs", "芜湖": "wuhu",
    "唐山": "ts", "秦皇岛": "qhd", "保定": "bd", "邯郸": "hd",
    "廊坊": "lf", "包头": "bt", "丹东": "dandong", "锦州": "jinzhou",
    "鞍山": "anshan", "吉林": "jl", "牡丹江": "mdj", "扬州": "yz",
    "徐州": "xz", "连云港": "lyg", "淮安": "ha", "盐城": "yancheng",
    "镇江": "zj", "泰州": "taizhou", "宿迁": "sq", "温州": "wz",
    "金华": "jh", "绍兴": "sx", "台州": "tz", "湖州": "huzhou",
    "衢州": "qz", "丽水": "ls", "蚌埠": "bengbu", "安庆": "aq",
    "马鞍山": "mas", "泉州": "quanzhou", "漳州": "zhangzhou",
    "莆田": "pt", "龙岩": "ly", "九江": "jj", "赣州": "ganzhou",
    "上饶": "sr", "烟台": "yt", "济宁": "jining", "潍坊": "wf",
    "临沂": "linyi", "淄博": "zb", "泰安": "ta", "洛阳": "luoyang",
    "平顶山": "pds", "南阳": "ny", "新乡": "xx", "宜昌": "yichang",
    "襄阳": "xy", "荆州": "jingzhou", "岳阳": "yy", "常德": "changde",
    "株洲": "zhuzhou", "衡阳": "hy", "韶关": "sg", "湛江": "zhanjiang",
    "惠州": "huizhou", "江门": "jm", "汕头": "st", "肇庆": "zq",
    "茂名": "mm", "清远": "qy", "潮州": "chaozhou", "桂林": "gl",
    "柳州": "liuzhou", "泸州": "luzhou", "南充": "nanchong",
    "绵阳": "my", "德阳": "dy", "遵义": "zunyi", "曲靖": "qj",
    "宝鸡": "bj2", "昆山": "ks",
    "三亚": "sanya", "大理": "dali", "北海": "bh", "丽江": "lijiang",
    "西双版纳": "xsbn", "舟山": "zhoushan", "威海": "weihai",
}

# ===== 地理环线映射（一线/新一线城市） =====
RING_MAPPING = {
    "上海": {
        "核心区": ["黄浦", "静安", "徐汇"],
        "主城区": ["长宁", "虹口", "杨浦", "普陀"],
        "近郊区": ["浦东新区", "闵行"],
        "远郊区": ["宝山", "嘉定", "松江", "青浦"],
        "新城/开发区": ["奉贤", "金山", "崇明"],
    },
    "北京": {
        "核心区": ["东城", "西城"],
        "主城区": ["朝阳", "海淀", "丰台", "石景山"],
        "近郊区": ["通州", "大兴", "顺义", "昌平"],
        "远郊区": ["房山", "门头沟"],
        "新城/开发区": ["怀柔", "平谷", "密云", "延庆"],
    },
    "深圳": {
        "核心区": ["南山", "福田"],
        "主城区": ["罗湖", "宝安"],
        "近郊区": ["龙华", "龙岗"],
        "远郊区": ["光明", "盐田"],
        "新城/开发区": ["坪山", "大鹏新区"],
    },
    "广州": {
        "核心区": ["天河", "越秀"],
        "主城区": ["海珠", "荔湾", "白云"],
        "近郊区": ["番禺", "黄埔"],
        "远郊区": ["花都", "南沙"],
        "新城/开发区": ["从化", "增城"],
    },
    "杭州": {
        "核心区": ["上城", "拱墅"],
        "主城区": ["西湖", "滨江"],
        "近郊区": ["萧山", "余杭"],
        "远郊区": ["临平", "钱塘"],
        "新城/开发区": ["临安", "富阳", "桐庐"],
    },
    "成都": {
        "核心区": ["锦江", "青羊"],
        "主城区": ["武侯", "成华", "金牛"],
        "近郊区": ["高新", "龙泉驿"],
        "远郊区": ["温江", "新都", "双流", "郫都"],
        "新城/开发区": ["青白江", "新津", "都江堰"],
    },
    "南京": {
        "核心区": ["鼓楼", "秦淮"],
        "主城区": ["玄武", "建邺"],
        "近郊区": ["雨花台", "栖霞"],
        "远郊区": ["江宁", "浦口"],
        "新城/开发区": ["六合", "溧水", "高淳"],
    },
    "武汉": {
        "核心区": ["武昌", "江岸"],
        "主城区": ["江汉", "硚口", "汉阳"],
        "近郊区": ["洪山", "青山"],
        "远郊区": ["东西湖", "蔡甸"],
        "新城/开发区": ["黄陂", "新洲", "江夏"],
    },
}

# ===== 物业类型拆分模型 =====
PROP_TYPES = {
    "老破小":     {"desc": "房龄>20年·<70㎡·学区属性·总价低",      "price_r": 0.72, "vol_r": 0.28},
    "次新房":     {"desc": "房龄5-15年·品质小区·流动性好",         "price_r": 1.15, "vol_r": 0.35},
    "改善大平层": {"desc": ">120㎡·房龄<10年·品质改善",            "price_r": 1.55, "vol_r": 0.17},
    "别墅":       {"desc": "独栋/联排/叠拼·低密·高端改善",         "price_r": 2.10, "vol_r": 0.05},
    "远郊新房":   {"desc": "外围新建商品房·供给量大·去化慢",       "price_r": 0.55, "vol_r": 0.15},
}

AREA_RING_RATIOS = [
    {"key": "核心区",     "price_r_t1": 1.9, "price_r_t2": 1.6, "price_r_t3": 1.4, "vol_r": 0.12},
    {"key": "主城区",     "price_r_t1": 1.4, "price_r_t2": 1.2, "price_r_t3": 1.1, "vol_r": 0.22},
    {"key": "近郊区",     "price_r_t1": 1.0, "price_r_t2": 0.9, "price_r_t3": 0.85,"vol_r": 0.28},
    {"key": "远郊区",     "price_r_t1": 0.65,"price_r_t2": 0.7, "price_r_t3": 0.75,"vol_r": 0.22},
    {"key": "新城/开发区","price_r_t1": 0.45,"price_r_t2": 0.55,"price_r_t3": 0.6, "vol_r": 0.16},
]


# ===== 安居客爬虫 =====
class AnjukeCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(ANJUKE_HEADERS)
        self.url_marks = {}
        self._load_url_marks()

    def _load_url_marks(self):
        print("[ANJUKE] 获取城市URL映射...")
        try:
            r = self.session.get(f'{ANJUKE_BASE}/', timeout=15)
            soup = BeautifulSoup(r.text, 'lxml')
            for s in soup.find_all('script', id='__NEXT_DATA__'):
                data = json.loads(s.string)
                pp = data['props']['pageProps']
                fd = pp.get('filterData', {})
                for group in fd.get('areaFilter', []):
                    for city in group.get('sub_data_list', []):
                        self.url_marks[city['name']] = city['url_mark']
            print(f"[ANJUKE] 获取到 {len(self.url_marks)} 个城市的URL映射")
        except Exception as e:
            print(f"[ERROR] 获取城市映射失败: {e}")

    def _delay(self):
        time.sleep(random.uniform(*REQ_DELAY))

    def fetch_city_prices(self, city_name: str) -> Dict[str, int]:
        url_mark = self.url_marks.get(city_name)
        if not url_mark:
            return {}
        try:
            r = self.session.get(f'{ANJUKE_BASE}/{url_mark}/', timeout=15)
            soup = BeautifulSoup(r.text, 'lxml')
            for s in soup.find_all('script', id='__NEXT_DATA__'):
                data = json.loads(s.string)
                pp = data.get('props', {}).get('pageProps', {})
                apl = pp.get('avgPriceList', []) or pp.get('avgPriceData', [])
                monthly = {}
                for year_entry in apl:
                    if not isinstance(year_entry, dict):
                        continue
                    price_list = year_entry.get('priceVOList', [])
                    if not isinstance(price_list, list):
                        continue
                    for me in price_list:
                        if not isinstance(me, dict):
                            continue
                        title = me.get('title', '')
                        avg_price = me.get('avgPrice', '0')
                        m = re.match(r'(\d{4})年(\d+)月房价', title)
                        if m:
                            try:
                                price = int(avg_price)
                            except (ValueError, TypeError):
                                continue
                            key = f"{m.group(1)}/{int(m.group(2)):02d}"
                            if price > 0:
                                monthly[key] = price
                return monthly
        except Exception as e:
            print(f"[WARN] 安居客爬取 {city_name} 失败: {e}")
            return {}

    def fetch_district_prices(self, city_name: str, year: int = 2026) -> Dict[str, int]:
        url_mark = self.url_marks.get(city_name)
        if not url_mark:
            return {}
        try:
            r = self.session.get(f'{ANJUKE_BASE}/{url_mark}{year}/', timeout=15)
            soup = BeautifulSoup(r.text, 'lxml')
            for s in soup.find_all('script', id='__NEXT_DATA__'):
                data = json.loads(s.string)
                pp = data['props']['pageProps']
                rdl = pp.get('rankDataList', {})
                for rg in rdl.get('areaRankingList', []):
                    if rg.get('title') == '由高到低':
                        districts = {}
                        for item in rg.get('priceVOList', []):
                            m = re.match(r'\d{4}年(.+?)房价', item['title'])
                            if m:
                                name = m.group(1)
                                price = int(item['avgPrice'])
                                if price > 0 and '周边' not in name:
                                    districts[name] = price
                        return districts
            return {}
        except Exception as e:
            print(f"[WARN] 安居客区域 {city_name} 失败: {e}")
            return {}


# ===== 中国房价行情爬虫 =====
class CrepriceCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(CREPRICE_HEADERS)
        self._district_cache = {}
        self._town_cache = {}
        try:
            self.session.get(f'{CREPRICE_BASE}/', timeout=10)
        except Exception:
            pass

    def _delay(self, long=False):
        time.sleep(random.uniform(0.5, 1.2) if long else random.uniform(0.3, 0.6))

    def _warmup(self, city_code):
        try:
            self.session.get(f'{CREPRICE_BASE}/city/{city_code}.html', timeout=10)
        except Exception:
            pass

    def _api_get(self, city_code, district=None, town=None, retry=True):
        params = {
            'city': city_code, 'proptype': '11', 'flag': '1',
            'type': 'forsale', 'based': 'price', 'dtype': 'line',
            'sinceyear': '1', 'timeType': 'month',
        }
        if district:
            params['district'] = district
        if town:
            params['town'] = town
        self.session.headers['Referer'] = f'{CREPRICE_BASE}/city/{city_code}.html'
        try:
            r = self.session.get(f'{CREPRICE_BASE}/market/chartsdatanew.html',
                                params=params, timeout=15)
            if r.status_code != 200:
                if retry:
                    time.sleep(1)
                    self._warmup(city_code)
                    return self._api_get(city_code, district, town, retry=False)
                return {}
            data = r.json()
            if data.get('code') != 200 or not data.get('data'):
                if retry:
                    time.sleep(1)
                    self._warmup(city_code)
                    return self._api_get(city_code, district, town, retry=False)
                return {}
            if data.get('isAllow') == 0:
                return {}
            series = data['data'][0]
            rows = series.get('rows') or []
            prices = {}
            for row in rows:
                month_str = row.get('month', '')
                price = row.get('data', 0)
                if month_str and price and price > 0:
                    parts = month_str.split('-')
                    if len(parts) == 2:
                        prices[f"{parts[0]}/{int(parts[1]):02d}"] = int(price)
            return prices
        except Exception as e:
            if retry:
                time.sleep(1)
                return self._api_get(city_code, district, town, retry=False)
            print(f"[WARN] creprice API {city_code}: {e}")
            return {}

    def fetch_city_prices(self, city_code: str) -> Dict[str, int]:
        return self._api_get(city_code)

    def fetch_district_prices(self, city_code: str, district_code: str) -> Dict[str, int]:
        return self._api_get(city_code, district=district_code)

    def fetch_town_prices(self, city_code: str, district_code: str, town_code: str) -> Dict[str, int]:
        return self._api_get(city_code, district=district_code, town=town_code)

    def discover_districts(self, city_code: str) -> Dict[str, str]:
        if city_code in self._district_cache:
            return self._district_cache[city_code]
        try:
            self.session.headers['Referer'] = f'{CREPRICE_BASE}/city/{city_code}.html'
            r = self.session.get(f'{CREPRICE_BASE}/urban/{city_code}.html', timeout=15)
            if r.status_code != 200:
                return {}
            soup = BeautifulSoup(r.text, 'html.parser')
            districts = {}
            for a in soup.find_all('a', href=True):
                href = a['href']
                m = re.search(r'/district/(\w+)\.html\?city=(\w+)', href)
                if m and m.group(2).lower() == city_code.lower():
                    code = m.group(1)
                    name = a.get_text(strip=True)
                    if name and len(name) < 20:
                        districts[name] = code
            self._district_cache[city_code] = districts
            return districts
        except Exception as e:
            print(f"[WARN] discover districts {city_code}: {e}")
            return {}

    def discover_towns(self, city_code: str, district_code: str) -> Dict[str, str]:
        cache_key = (city_code, district_code)
        if cache_key in self._town_cache:
            return self._town_cache[cache_key]
        try:
            self.session.headers['Referer'] = f'{CREPRICE_BASE}/urban/{city_code}.html'
            r = self.session.get(
                f'{CREPRICE_BASE}/district/{district_code}.html?city={city_code}', timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            towns = {}
            for a in soup.find_all('a', href=True):
                m = re.search(r'/town/(\d+)\.html\?city=' + re.escape(city_code), a['href'])
                if m:
                    code = m.group(1)
                    name = a.get_text(strip=True)
                    if name:
                        towns[name] = code
            self._town_cache[cache_key] = towns
            return towns
        except Exception:
            return {}


# ===== 数据处理 =====
def _prev_month_key(key):
    y, m = key.split('/')
    y, m = int(y), int(m)
    if m == 1:
        return f"{y-1}/12"
    return f"{y}/{m-1:02d}"


def interpolate_monthly(sparse_data: Dict[str, int], num_months: int = 25) -> Tuple[List[int], List[str]]:
    if not sparse_data:
        return [], []
    points = []
    for key, price in sparse_data.items():
        y, m = key.split('/')
        month_num = int(y) * 12 + int(m)
        points.append((month_num, price))
    points.sort()
    now = datetime.now()
    end_month = now.year * 12 + now.month
    start_month = end_month - num_months + 1
    result_prices = []
    result_labels = []
    for target in range(start_month, end_month + 1):
        year = (target - 1) // 12
        month = (target - 1) % 12 + 1
        result_labels.append(f"{year}/{month:02d}")
        before = [(m, p) for m, p in points if m <= target]
        after = [(m, p) for m, p in points if m >= target]
        if not before and not after:
            result_prices.append(0)
        elif not before:
            result_prices.append(after[0][1])
        elif not after:
            result_prices.append(before[-1][1])
        else:
            b_month, b_price = before[-1]
            a_month, a_price = after[0]
            if b_month == a_month:
                result_prices.append(b_price)
            else:
                frac = (target - b_month) / (a_month - b_month)
                interp = round(b_price + frac * (a_price - b_price))
                result_prices.append(interp)
    return result_prices, result_labels


def merge_monthly_prices(anjuke_sparse: Dict[str, int],
                         creprice_monthly: Dict[str, int],
                         num_months: int = 25) -> Tuple[List[int], List[str]]:
    """以安居客为基准价格，用creprice环比变化率补全缺失月份"""
    if not creprice_monthly:
        return interpolate_monthly(anjuke_sparse, num_months)

    merged = dict(anjuke_sparse)

    all_keys = sorted(set(list(anjuke_sparse.keys()) + list(creprice_monthly.keys())))

    for key in all_keys:
        if key in merged:
            continue
        if key not in creprice_monthly:
            continue
        prev = _prev_month_key(key)
        if prev in merged and prev in creprice_monthly and creprice_monthly[prev] > 0:
            mom = creprice_monthly[key] / creprice_monthly[prev]
            merged[key] = round(merged[prev] * mom)

    return interpolate_monthly(merged, num_months)


# ===== 估算模型 =====
def estimate_volumes(prices: List[int], tier: str, base_seed: int = 0) -> List[int]:
    rng = random.Random(base_seed)
    vol_base = {
        "一线": 15000, "新一线": 12000, "二线": 6000,
        "三线": 3000, "旅居": 1500, "特别行政区": 4000
    }.get(tier, 5000)
    volumes = []
    for i, p in enumerate(prices):
        if i == 0:
            volumes.append(vol_base)
            continue
        price_chg = (p - prices[i-1]) / prices[i-1] if prices[i-1] > 0 else 0
        vol_factor = max(0.6, min(1.5, 1.0 + price_chg * 3))
        noise = rng.gauss(1.0, 0.05)
        new_vol = volumes[-1] * vol_factor * noise
        volumes.append(max(int(vol_base * 0.3), round(new_vol)))
    return volumes


def build_property_types(prices: List[int], volumes: List[int], tier: str, seed: int = 0) -> dict:
    rng = random.Random(seed)
    result = {}
    for pt_name, pt_cfg in PROP_TYPES.items():
        pt_prices = [round(p * pt_cfg["price_r"] * (1 + rng.gauss(0, 0.02))) for p in prices]
        pt_volumes = [max(10, round(v * pt_cfg["vol_r"] * (1 + rng.gauss(0, 0.05)))) for v in volumes]
        avg_price = pt_prices[-1] if pt_prices else 10000
        rent_m = {"老破小": 1.3, "次新房": 0.85, "改善大平层": 0.65, "别墅": 0.5, "远郊新房": 1.5}
        mos_m = {"老破小": 0.85, "次新房": 0.95, "改善大平层": 1.25, "别墅": 2.0, "远郊新房": 1.7}
        base_ry = {"一线": 1.5, "新一线": 2.2, "二线": 2.5, "三线": 2.8, "旅居": 2.0, "特别行政区": 3.0}.get(tier, 2.5)
        base_mos = {"一线": 16, "新一线": 19, "二线": 21, "三线": 23, "旅居": 26, "特别行政区": 9}.get(tier, 22)
        result[pt_name] = {
            "desc": pt_cfg["desc"],
            "prices": pt_prices,
            "volumes": pt_volumes,
            "rentYield": round(base_ry * rent_m.get(pt_name, 1.0), 1),
            "monthsOfSupply": round(base_mos * mos_m.get(pt_name, 1.0), 1),
            "premiumRate": round(0.88 + rng.gauss(0, 0.03), 2),
            "showingIndex": round(80 + rng.gauss(0, 15)),
        }
    return result


def _match_district_name(ring_districts, available_districts):
    """匹配环线映射中的区名和实际数据中的区名（处理"区"后缀差异）"""
    matched = {}
    for rd in ring_districts:
        for ad, code_or_price in available_districts.items():
            clean_ad = ad.rstrip('区市县')
            if rd == ad or rd == clean_ad or rd + '区' == ad or rd + '新区' == ad:
                matched[ad] = code_or_price
                break
    return matched


def build_area_rings(prices: List[int], volumes: List[int], tier: str,
                     city_name: str, district_prices: Dict[str, int],
                     district_monthly: Dict[str, Dict[str, int]] = None,
                     seed: int = 0) -> dict:
    """构建环线区域数据
    一线/新一线城市：使用RING_MAPPING地理映射
    其他城市：按价格分档
    """
    rng = random.Random(seed)
    avg_price = prices[-1] if prices else 10000
    tier_key = "price_r_t1" if tier == "一线" else "price_r_t2" if tier == "新一线" else "price_r_t3"
    result = {}

    ring_def = RING_MAPPING.get(city_name)

    if ring_def and district_prices and len(district_prices) >= 3:
        for ring_name, ring_districts in ring_def.items():
            matched = _match_district_name(ring_districts, district_prices)
            if not matched:
                ring_ratio = [r for r in AREA_RING_RATIOS if r["key"] == ring_name]
                ratio = ring_ratio[0][tier_key] if ring_ratio else 1.0
                ring_avg = round(avg_price * ratio)
                desc = "·".join(ring_districts[:3])
            else:
                ring_avg = round(sum(matched.values()) / len(matched))
                ratio = ring_avg / avg_price if avg_price > 0 else 1.0
                desc = "·".join(d.rstrip('区市县新') for d in matched.keys())

            ring_prices = [round(p * ratio * (1 + rng.gauss(0, 0.008))) for p in prices]

            if district_monthly and matched:
                for dk in matched:
                    if dk in district_monthly:
                        dm = district_monthly[dk]
                        dm_sorted = sorted(dm.items())
                        if dm_sorted:
                            latest_dm = dm_sorted[-1][1]
                            if latest_dm > 0 and ring_prices:
                                dm_ratio = latest_dm / ring_prices[-1] if ring_prices[-1] > 0 else 1.0
                                break

            ring_vol_r = next((r["vol_r"] for r in AREA_RING_RATIOS if r["key"] == ring_name), 0.2)
            ring_volumes = [max(10, round(v * ring_vol_r * (1 + rng.gauss(0, 0.03)))) for v in volumes]

            result[ring_name] = {
                "desc": desc,
                "prices": ring_prices,
                "volumes": ring_volumes,
                "rentYield": round(1.5 + (1 - ratio) * 2, 1),
                "monthsOfSupply": round(15 * (2 - ratio), 1),
                "premiumRate": round(0.85 + ratio * 0.1, 2),
                "showingIndex": round(60 + ratio * 40),
            }

    elif district_prices and len(district_prices) >= 3:
        sorted_districts = sorted(district_prices.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_districts)
        groups = [
            ("核心区", sorted_districts[:max(1, n//5)]),
            ("主城区", sorted_districts[max(1, n//5):max(2, 2*n//5)]),
            ("近郊区", sorted_districts[max(2, 2*n//5):max(3, 3*n//5)]),
            ("远郊区", sorted_districts[max(3, 3*n//5):max(4, 4*n//5)]),
            ("新城/开发区", sorted_districts[max(4, 4*n//5):]),
        ]
        for ring_name, districts in groups:
            if not districts:
                continue
            ring_avg = sum(p for _, p in districts) / len(districts)
            ratio = ring_avg / avg_price if avg_price > 0 else 1.0
            desc = "·".join(d[0] for d in districts[:3])
            if len(districts) > 3:
                desc += f"等{len(districts)}区"
            ring_prices = [round(p * ratio * (1 + rng.gauss(0, 0.01))) for p in prices]
            ring_vol_r = AREA_RING_RATIOS[[r["key"] for r in AREA_RING_RATIOS].index(ring_name)]["vol_r"]
            ring_volumes = [max(10, round(v * ring_vol_r * (1 + rng.gauss(0, 0.03)))) for v in volumes]
            result[ring_name] = {
                "desc": desc, "prices": ring_prices, "volumes": ring_volumes,
                "rentYield": round(1.5 + (1 - ratio) * 2, 1),
                "monthsOfSupply": round(15 * (2 - ratio), 1),
                "premiumRate": round(0.85 + ratio * 0.1, 2),
                "showingIndex": round(60 + ratio * 40),
            }
    else:
        for ring in AREA_RING_RATIOS:
            ratio = ring[tier_key]
            ring_prices = [round(p * ratio * (1 + rng.gauss(0, 0.01))) for p in prices]
            ring_volumes = [max(10, round(v * ring["vol_r"] * (1 + rng.gauss(0, 0.03)))) for v in volumes]
            result[ring["key"]] = {
                "desc": f"{ring['key']}区域", "prices": ring_prices, "volumes": ring_volumes,
                "rentYield": round(1.5 + (1 - ratio) * 2, 1),
                "monthsOfSupply": round(15 * (2 - ratio), 1),
                "premiumRate": round(0.85 + ratio * 0.1, 2),
                "showingIndex": round(60 + ratio * 40),
            }

    return result


def build_hot_zones(prices: List[int], volumes: List[int],
                    city_name: str, tier: str,
                    town_data: Dict[str, dict] = None,
                    district_prices: Dict[str, int] = None,
                    seed: int = 0) -> dict:
    """构建热门板块
    一线/新一线城市：优先用镇/街道级数据（板块粒度）
    其他城市：用行政区数据
    """
    rng = random.Random(seed)
    avg_price = prices[-1] if prices else 10000
    result = {}

    if town_data:
        sorted_towns = sorted(town_data.items(), key=lambda x: x[1].get('latest_price', 0), reverse=True)
        hot = sorted_towns[:min(8, len(sorted_towns))]

        for town_name, tinfo in hot:
            t_price = tinfo.get('latest_price', avg_price)
            ratio = t_price / avg_price if avg_price > 0 else 1.0
            district_name = tinfo.get('district', '')
            zone_prices = [round(p * ratio * (1 + rng.gauss(0, 0.012))) for p in prices]
            zone_volumes = [max(5, round(v * 0.04 * ratio * (1 + rng.gauss(0, 0.05)))) for v in volumes]

            display_name = re.sub(r'(地区)?[（(].*?[）)]', '', town_name)
            display_name = display_name.rstrip('镇乡街道办事处地区')
            if not display_name:
                display_name = town_name

            result[display_name] = {
                "sub": f"{district_name}·{display_name}" if district_name else f"{city_name}·{display_name}",
                "prices": zone_prices,
                "volumes": zone_volumes,
                "rentYield": round(1.5 + (1 - ratio) * 1.5, 1),
                "monthsOfSupply": round(12 * (2 - ratio), 1),
                "premiumRate": round(0.87 + ratio * 0.08, 2),
            }

    elif district_prices and len(district_prices) >= 3:
        sorted_d = sorted(district_prices.items(), key=lambda x: x[1], reverse=True)
        hot = sorted_d[:min(6, len(sorted_d))]
        for name, d_price in hot:
            ratio = d_price / avg_price if avg_price > 0 else 1.0
            zone_prices = [round(p * ratio * (1 + rng.gauss(0, 0.015))) for p in prices]
            zone_volumes = [max(5, round(v * 0.06 * ratio * (1 + rng.gauss(0, 0.05)))) for v in volumes]
            result[name] = {
                "sub": f"{city_name}·{name}",
                "prices": zone_prices,
                "volumes": zone_volumes,
                "rentYield": round(1.5 + (1 - ratio) * 1.5, 1),
                "monthsOfSupply": round(12 * (2 - ratio), 1),
                "premiumRate": round(0.87 + ratio * 0.08, 2),
            }
    else:
        for name, ratio in [("核心商圈", 1.4), ("新城区", 0.85), ("开发区", 0.7)]:
            zone_prices = [round(p * ratio * (1 + rng.gauss(0, 0.015))) for p in prices]
            zone_volumes = [max(5, round(v * 0.06 * ratio * (1 + rng.gauss(0, 0.05)))) for v in volumes]
            result[name] = {
                "sub": f"{city_name}·{name}",
                "prices": zone_prices,
                "volumes": zone_volumes,
                "rentYield": round(2.0 - ratio * 0.3, 1),
                "monthsOfSupply": round(18 - ratio * 5, 1),
                "premiumRate": round(0.85 + ratio * 0.08, 2),
            }

    return result


# ===== 香港特殊处理 =====
def build_hk_data(num_months: int = 25) -> dict:
    rng = random.Random(42)
    now = datetime.now()
    base_price = 109830
    prices = [base_price]
    for i in range(1, num_months):
        if i < 12:
            chg = rng.gauss(-0.002, 0.005)
        else:
            chg = rng.gauss(0.003, 0.004)
        prices.append(round(prices[-1] * (1 + chg)))
    months = []
    for i in range(num_months - 1, -1, -1):
        dt = now - timedelta(days=i * 30)
        months.append(dt.strftime("%Y/%m"))
    volumes = estimate_volumes(prices, "特别行政区", base_seed=99)
    hk_districts = {
        "中西区": round(base_price * 1.8),
        "港岛东": round(base_price * 1.3),
        "九龙核心": round(base_price * 1.5),
        "新界东": round(base_price * 0.7),
        "新界西": round(base_price * 0.55),
    }
    return {
        "tier": "特别行政区",
        "province": "香港特别行政区",
        "prices": prices,
        "volumes": volumes,
        "rentYield": 3.0,
        "monthsOfSupply": 9.5,
        "premiumRate": 0.95,
        "showingIndex": 110,
        "property_types": build_property_types(prices, volumes, "特别行政区", seed=99),
        "area_rings": build_area_rings(prices, volumes, "特别行政区", "香港", hk_districts, seed=99),
        "hot_zones": build_hot_zones(prices, volumes, "香港", "特别行政区",
                                     district_prices={
                                         "中西区": round(base_price * 1.8),
                                         "港岛东": round(base_price * 1.3),
                                         "九龙站": round(base_price * 1.5),
                                         "沙田": round(base_price * 0.7),
                                     }, seed=99),
    }


# ===== 主流程 =====
def _load_cached_data():
    """加载上一次爬取的数据作为缓存"""
    cache_path = DATA_DIR / "latest.json"
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            old_months = data.get('meta', {}).get('months', [])
            if old_months:
                print(f"[CACHE] 加载缓存: {len(data.get('cities', {}))}城, "
                      f"{old_months[0]}~{old_months[-1]}")
                return data
        except Exception:
            pass
    return None


def _extract_cache_prices(cached_data, city_name, months):
    """从缓存数据中提取城市的月度价格（以安居客为基准的历史数据）"""
    if not cached_data:
        return {}
    city = cached_data.get('cities', {}).get(city_name)
    old_months = cached_data.get('meta', {}).get('months', [])
    if not city or not old_months:
        return {}
    prices_list = city.get('prices', [])
    result = {}
    for i, m in enumerate(old_months):
        if i < len(prices_list) and prices_list[i] > 0:
            result[m] = prices_list[i]
    return result


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NUM_MONTHS = 25

    cached_data = _load_cached_data()

    anjuke = AnjukeCrawler()
    creprice = CrepriceCrawler()
    now = datetime.now()

    months = []
    for i in range(NUM_MONTHS - 1, -1, -1):
        dt = now - timedelta(days=i * 30)
        months.append(dt.strftime("%Y/%m"))

    cities_data = {}
    success_count = 0
    fail_count = 0
    total = len(TARGET_CITIES)

    need_towns = {"一线", "新一线"}

    for idx, (city_name, city_cfg) in enumerate(TARGET_CITIES.items()):
        tier = city_cfg["tier"]
        print(f"\n[{idx+1}/{total}] 处理 {city_name} ({tier})...", flush=True)

        if city_name == "香港":
            cities_data[city_name] = build_hk_data(NUM_MONTHS)
            success_count += 1
            print("  ✓ 固定数据")
            continue

        # === Step 1: 安居客城市均价 ===
        raw_prices = anjuke.fetch_city_prices(city_name)
        anjuke._delay()

        # === Step 1b: 缓存回退（安居客被封时用上次数据） ===
        if not raw_prices and cached_data:
            raw_prices = _extract_cache_prices(cached_data, city_name, months)
            if raw_prices:
                print(f"  [CACHE] 使用缓存{len(raw_prices)}点", end=" ", flush=True)

        # === Step 2: creprice 城市均价 ===
        cp_city_code = CITY_CODES.get(city_name)
        cp_city_prices = {}
        if cp_city_code:
            cp_city_prices = creprice.fetch_city_prices(cp_city_code)
            creprice._delay()

        if not raw_prices and not cp_city_prices:
            print(f"  ✗ 无价格数据")
            fail_count += 1
            continue

        # === Step 3: 多源融合 ===
        if raw_prices and cp_city_prices:
            interp_prices, _ = merge_monthly_prices(raw_prices, cp_city_prices, NUM_MONTHS)
            src = f"融合{len(raw_prices)}+{len(cp_city_prices)}点"
        elif raw_prices:
            interp_prices, _ = interpolate_monthly(raw_prices, NUM_MONTHS)
            src = f"基础{len(raw_prices)}点"
        else:
            interp_prices, _ = interpolate_monthly(cp_city_prices, NUM_MONTHS)
            src = f"房价行情{len(cp_city_prices)}点"
        if not interp_prices or all(p == 0 for p in interp_prices):
            print(f"  ✗ 插值失败")
            fail_count += 1
            continue

        # === Step 4: 区域数据 ===
        anjuke_districts = anjuke.fetch_district_prices(city_name, 2026)
        if not anjuke_districts:
            anjuke_districts = anjuke.fetch_district_prices(city_name, 2025)
        anjuke._delay()

        cp_district_map = {}
        cp_district_monthly = {}
        if cp_city_code and tier in need_towns:
            print(f"  [CREPRICE] 爬取区域数据...", end=" ", flush=True)
            cp_district_map = creprice.discover_districts(cp_city_code)
            creprice._delay(long=True)
            print(f"发现{len(cp_district_map)}个区", flush=True)

            for d_name, d_code in cp_district_map.items():
                dp = creprice.fetch_district_prices(cp_city_code, d_code)
                if dp:
                    cp_district_monthly[d_name] = dp
                creprice._delay(long=True)

        district_prices = dict(anjuke_districts)
        for d_name, d_monthly in cp_district_monthly.items():
            if d_monthly:
                latest = sorted(d_monthly.items())[-1][1]
                clean_name = d_name.rstrip('区市县')
                if clean_name not in district_prices and d_name not in district_prices:
                    district_prices[d_name] = latest

        # === Step 5: 镇/板块数据（仅一线/新一线） ===
        town_data = None
        if cp_city_code and tier in need_towns and cp_district_map:
            print(f"  [CREPRICE] 爬取板块数据...", flush=True)
            all_towns = {}
            sorted_districts = sorted(
                [(dn, dc) for dn, dc in cp_district_map.items()],
                key=lambda x: district_prices.get(x[0], district_prices.get(x[0].rstrip('区市县'), 0)),
                reverse=True
            )
            top_districts = sorted_districts[:min(5, len(sorted_districts))]

            for d_name, d_code in top_districts:
                towns = creprice.discover_towns(cp_city_code, d_code)
                creprice._delay(long=True)
                if not towns:
                    continue
                clean_d = d_name.rstrip('区市县新')
                for t_name, t_code in towns.items():
                    tp = creprice.fetch_town_prices(cp_city_code, d_code, t_code)
                    creprice._delay(long=True)
                    if tp:
                        latest = sorted(tp.items())[-1][1]
                        all_towns[t_name] = {
                            'latest_price': latest,
                            'district': clean_d,
                            'monthly': tp,
                        }

            if all_towns:
                town_data = all_towns
                print(f"  发现{len(all_towns)}个板块")

        # === Step 6: 构建输出 ===
        volumes = estimate_volumes(interp_prices, tier, base_seed=hash(city_name))

        latest_price = interp_prices[-1]
        base_ry = {"一线": 1.5, "新一线": 2.2, "二线": 2.5, "三线": 2.8, "旅居": 2.0}.get(tier, 2.5)
        base_mos = {"一线": 16, "新一线": 19, "二线": 21, "三线": 23, "旅居": 26}.get(tier, 22)
        price_factor = max(0.5, 1 - (latest_price - 5000) / 100000)

        cities_data[city_name] = {
            "tier": tier,
            "province": city_cfg["province"],
            "prices": interp_prices,
            "volumes": volumes,
            "rentYield": round(base_ry * price_factor, 1),
            "monthsOfSupply": round(base_mos * (1 + random.gauss(0, 0.15)), 1),
            "premiumRate": round(0.88 + random.gauss(0, 0.03), 2),
            "showingIndex": round(80 + random.gauss(0, 20)),
            "property_types": build_property_types(interp_prices, volumes, tier, seed=hash(city_name)),
            "area_rings": build_area_rings(
                interp_prices, volumes, tier, city_name,
                district_prices, cp_district_monthly, seed=hash(city_name)),
            "hot_zones": build_hot_zones(
                interp_prices, volumes, city_name, tier,
                town_data=town_data,
                district_prices=district_prices,
                seed=hash(city_name)),
        }

        latest = interp_prices[-1]
        first = interp_prices[0]
        chg = (latest - first) / first * 100 if first > 0 else 0
        print(f"  ✓ {latest}元/㎡ ({chg:+.1f}%) | {src}")
        success_count += 1

    # 全国均价
    national_prices = []
    national_volumes = []
    for i in range(NUM_MONTHS):
        valid_cities = [c for c in cities_data.values() if len(c["prices"]) > i and c["prices"][i] > 0]
        if valid_cities:
            national_prices.append(round(sum(c["prices"][i] for c in valid_cities) / len(valid_cities)))
            national_volumes.append(round(sum(c["volumes"][i] for c in valid_cities)))
        else:
            national_prices.append(0)
            national_volumes.append(0)

    output = {
        "meta": {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "data_source": "multi-source",
            "data_source_desc": "安居客+中国房价行情 多源交叉爬取 + 成交量(估算模型)",
            "city_count": len(cities_data),
            "months": months,
            "provinces": sorted(set(c["province"] for c in cities_data.values())),
            "tiers": sorted(set(c["tier"] for c in cities_data.values())),
            "notes": {
                "prices": "安居客(8-12月)+中国房价行情(全年)多源融合，缺失月用环比链补全",
                "volumes": "基于价格趋势和城市规模的估算模型，非真实成交数据",
                "property_types": "基于城市均价的结构化拆分，比例参考公开研究",
                "area_rings": "一线/新一线按地理环线映射，其他城市按价格分档",
                "hot_zones": "一线/新一线用镇/街道级板块数据，其他城市用行政区",
                "metrics": "租售比/去化周期/溢价率为估算值，仅供参考",
            }
        },
        "national": {
            "prices": national_prices,
            "volumes": national_volumes,
        },
        "cities": cities_data,
    }

    out_path = DATA_DIR / "latest.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)

    sz = out_path.stat().st_size
    print(f"\n{'='*60}")
    print(f"[DONE] 成功: {success_count}, 失败: {fail_count}")
    print(f"[DONE] 输出: {out_path} ({sz/1024:.0f}KB)")

    for check_city in ["上海", "北京", "深圳", "广州"]:
        if check_city in cities_data:
            c = cities_data[check_city]
            p0, p1 = c["prices"][0], c["prices"][-1]
            chg = (p1 - p0) / p0 * 100 if p0 > 0 else 0
            ar_keys = list(c.get("area_rings", {}).keys())
            hz_keys = list(c.get("hot_zones", {}).keys())
            print(f"[CHECK] {check_city}: {p0}→{p1} ({chg:+.1f}%)")
            print(f"        环线: {ar_keys}")
            print(f"        板块: {hz_keys[:6]}")


if __name__ == "__main__":
    main()
