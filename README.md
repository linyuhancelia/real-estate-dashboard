# 🏠 房产趋势看板 v5.0

全国124城量化视角的房地产市场趋势跟踪看板，辅助家庭购房决策。

## 📊 在线预览

**Aone Pages**: [https://real-estate-dashboard.io.alibaba-inc.com](https://real-estate-dashboard.io.alibaba-inc.com)

## ✨ 核心功能

| 模块 | 说明 |
|------|------|
| 📈 全国走势 | 上海 vs 全国大盘对比 + Top1异动城市 |
| 🏙️ 城市矩阵 | 124城卡片，按趋势温度/RS排序 |
| 🔍 城市详情 | 单城市深度分析面板 |
| 🏢 物业类型 | 老破小/次新房/改善大平层/别墅/远郊新房 |
| 🔥 热门板块 | 各城市核心板块走势 |
| 🎯 环线/区域 | 核心区→新城5级环线对比 |
| 🚦 止跌回升信号 | 严格递进：止跌→走平→回升 |
| 🏆 核心指标排行 | RS/租售比/去化周期排序 |
| 📊 量价关系 | 6种量价组合诊断 |

## 📡 数据来源

- **价格数据**: 安居客(anjuke.com) 二手房挂牌均价 **（真实爬取）**
- **区域均价**: 安居客行政区数据 **（真实爬取）**
- **成交量**: 基于价格趋势的估算模型
- **物业类型**: 基于城市均价的结构化拆分模型

## 🛠️ 技术栈

- 纯HTML单页应用，零框架依赖
- Chart.js 4.4.4 图表渲染
- PWA 支持 (Service Worker + Manifest)
- 移动端优先响应式设计

## 🚀 运行

```bash
# 安装依赖
pip install requests beautifulsoup4 lxml

# 爬取最新数据
python scripts/fetch_data.py

# 本地预览
npx serve .
```

## 📁 项目结构

```
├── index.html          # 看板主页（单文件应用）
├── chart.min.js        # Chart.js 本地副本
├── latest.json         # 数据文件（根目录副本）
├── data/
│   └── latest.json     # 爬虫输出数据
├── scripts/
│   └── fetch_data.py   # 安居客数据爬虫
├── manifest.json       # PWA manifest
├── sw.js               # Service Worker
└── icon-192.png        # PWA 图标
```

## 📋 路线图

- [x] Phase A: 移动端Web看板 (v1.0~v5.0)
- [ ] Phase B: 微信小程序版本
- [ ] 对接更多真实数据源 (贝壳/链家/中指院)
- [ ] GitHub Actions 定时自动更新

## ⚠️ 免责声明

本看板仅供趋势分析参考，不构成任何投资建议。价格数据来自安居客平台挂牌均价（非成交价），成交量为估算值。
