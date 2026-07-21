var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var dataService = require('../../utils/data')
var app = getApp()

var PERIOD_MAP = { '6月': 7, '1年': 13, '2年': 25 }

Page({
  data: {
    loaded: false,
    cityLoaded: false,
    detailLoaded: false,
    currentCity: '上海',
    searchText: '',
    suggestions: [],
    allCityNames: [],
    favCities: [],
    provinces: [],
    provCities: [],
    fProv: '',
    fCity: '',
    cityName: '',
    tier: '',
    province: '',
    priceStr: '',
    rentYield: 0,
    monthsOfSupply: 0,
    premiumRate: 0,
    showingIndex: 0,
    temp: {},
    rs: 0,
    rsColor: '#999',
    signals: {},
    changes: [],
    judge: {},
    vpDiag: null,
    trendPeriod: '1年',
    activeTab: 'property',
    activeSignals: [],
    inactiveSignals: [],
    inactiveCount: 0,
    showInactive: false,
    sigSummary: {},
    ptList: [],
    ptInsight: null,
    hzList: [],
    hzInsight: null,
    hzSort: 'price',
    hzDistricts: [],
    hzDistrictIdx: 0,
    hzShowFilter: false,
    arList: [],
    arInsight: null
  },

  onLoad: function() {
    this._loadFav()
    var self = this
    app.onDataReady(function() {
      var g = app.globalData
      var names = Object.keys(g.cities).sort()
      var provinces = [''].concat(g.meta.provinces || [])
      self._allNames = names
      self.setData({ loaded: true, allCityNames: names, provinces: provinces })
      self._selectCity(self.data.currentCity)
    })
  },

  onShow: function() {
    this._loadFav()
    if (app.globalData.loaded && !this.data.loaded) {
      var g = app.globalData
      var names = Object.keys(g.cities).sort()
      this._allNames = names
      this.setData({ loaded: true, allCityNames: names })
      this._selectCity(this.data.currentCity)
    }
  },

  _loadFav: function() {
    try {
      var fav = wx.getStorageSync('fav_cities') || []
      this.setData({ favCities: fav })
    } catch (e) {}
  },

  onSelectCity: function(e) {
    this._selectCity(e.currentTarget.dataset.name)
  },

  onProvChange: function(e) {
    var prov = this.data.provinces[e.detail.value] || ''
    var g = app.globalData
    var cities = g.cities
    var provCities = ['']
    if (prov) {
      (this._allNames || []).forEach(function(n) {
        if (cities[n] && cities[n].province === prov) provCities.push(n)
      })
    }
    this.setData({ fProv: prov, fCity: '', provCities: provCities })
  },

  onCityPick: function(e) {
    var city = this.data.provCities[e.detail.value] || ''
    if (!city) return
    this.setData({ fCity: city })
    this._selectCity(city)
  },

  onSearch: function(e) {
    this.setData({ searchText: (e.detail.value || '').trim() })
    this._updateSuggestions()
  },

  onSearchConfirm: function() {
    var keyword = this.data.searchText
    if (!keyword) return
    var g = app.globalData
    var match = (this._allNames || []).filter(function(n) {
      return n.indexOf(keyword) >= 0
    })
    if (match.length === 1) {
      this._selectCity(match[0])
    } else if (match.length > 1) {
      this.setData({ suggestions: match.slice(0, 12) })
    }
  },

  _updateSuggestions: function() {
    var g = app.globalData
    var cities = g.cities
    var keyword = this.data.searchText

    if (!keyword) {
      this.setData({ suggestions: [] })
      return
    }

    var results = (this._allNames || []).filter(function(n) {
      return n.indexOf(keyword) >= 0
    }).slice(0, 12)
    this.setData({ suggestions: results })
  },

  _selectCity: function(name) {
    var g = app.globalData
    var d = g.cities[name]
    if (!d) return

    this.setData({ searchText: '', suggestions: '', currentCity: name, detailLoaded: false })

    var lp = d.prices[d.prices.length - 1]
    var wc = algo.cC(d.prices, 1) / 4
    var mc = algo.cC(d.prices, 1)
    var m3 = algo.cC(d.prices, 3)
    var yc = algo.cC(d.prices, 12)

    var tp = algo.cTp(d.prices, d.volumes)
    var rs = algo.cRS(d.prices, g.allPrices, g.national.prices)
    var sg = algo.dSg(d.prices, d.volumes)
    var judge = algo.mktJudge(d.prices, d.volumes)
    var vp = algo.vpDx(d.prices, d.volumes)
    var vpClsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }

    this._cityData = d
    this._natData = g.national

    this.setData({
      cityLoaded: true,
      cityName: name,
      tier: d.tier,
      province: d.province,
      priceStr: lp.toLocaleString(),
      rentYield: d.rentYield,
      monthsOfSupply: d.monthsOfSupply,
      premiumRate: (d.premiumRate * 100).toFixed(0),
      showingIndex: d.showingIndex,
      temp: tp,
      rs: rs,
      rsColor: rs >= 60 ? '#2d8c4e' : rs >= 40 ? '#e67e22' : '#c0392b',
      signals: sg.s,
      changes: [
        { label: '近1周', val: fmt.fc(wc), cls: fmt.vcClass(wc) },
        { label: '近1月', val: fmt.fc(mc), cls: fmt.vcClass(mc) },
        { label: '近3月', val: fmt.fc(m3), cls: fmt.vcClass(m3) },
        { label: '近1年', val: fmt.fc(yc), cls: fmt.vcClass(yc) }
      ],
      judge: judge,
      vpDiag: { label: vp.label, cls: vpClsMap[vp.label] || 'ti' }
    })

    this._buildSignals(name, d)
    this._drawTrendIfReady()
    this._loadDetail(name)
  },

  _buildSignals: function(name, d) {
    var targets = [{ name: name + '(整体)', type: '城市', p: d.prices, v: d.volumes }]
    this._signalTargets = targets.map(function(t) {
      var r = algo.dSg(t.p, t.v)
      return { name: t.name, type: t.type, s: r.s, d: r.d }
    })
    this._rebuildSignalDisplay()
  },

  _rebuildSignalDisplay: function() {
    var targets = this._signalTargets || []
    var onC = 0, stC = 0, rcC = 0
    targets.forEach(function(t) {
      if (t.s.sd) onC++
      if (t.s.st) stC++
      if (t.s.rc) rcC++
    })
    var tt = targets.length
    var text = tt + '个市场：' + onC + '止跌·' + stC + '走平·' + rcC + '回升'
    var rcPct = tt ? (rcC / tt * 100).toFixed(0) : 0
    var stPct = tt ? (stC / tt * 100).toFixed(0) : 0
    var sdPct = tt ? (onC / tt * 100).toFixed(0) : 0
    var verdict = rcPct > 30 ? '回暖信号广泛，转折信心较强' :
      stPct > 40 ? '多数走平，等待方向选择' :
      sdPct > 40 ? '止跌信号初现，尚需确认' :
      '下行通道未改，建议继续观望'
    var cls = rcPct > 30 ? 'tp' : stPct > 40 ? 'tn' : sdPct > 40 ? 'tn' : 'tng'

    this.setData({
      activeSignals: targets.filter(function(t) { return t.s.sd || t.s.st || t.s.rc }),
      inactiveSignals: targets.filter(function(t) { return !t.s.sd && !t.s.st && !t.s.rc }),
      inactiveCount: targets.filter(function(t) { return !t.s.sd && !t.s.st && !t.s.rc }).length,
      showInactive: false,
      sigSummary: { text: text, verdict: verdict, cls: cls }
    })
  },

  _loadDetail: function(name) {
    var self = this
    dataService.loadCityDetail(name).then(function(detail) {
      if (detail.property_types) self._buildPropertyTypes(detail.property_types)
      if (detail.hot_zones) self._buildHotZones(detail.hot_zones)
      if (detail.area_rings) self._buildAreaRings(detail.area_rings)
      self.setData({ detailLoaded: true })
    }).catch(function() {
      self.setData({ detailLoaded: true })
    })
  },

  _buildPropertyTypes: function(pts) {
    var ptList = []
    var upCount = 0
    var names = Object.keys(pts)
    var targets = this._signalTargets

    names.forEach(function(n) {
      var v = pts[n]
      var p = v.prices, vol = v.volumes
      var lp = p[p.length - 1]
      var mc = algo.cC(p, 1), m3 = algo.cC(p, 3), yc = algo.cC(p, 12)
      var tp = algo.cTp(p, vol)
      var sg = algo.dSg(p, vol)
      var vp = algo.vpDx(p, vol)
      var vpClsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }
      if (yc > 0) upCount++
      targets.push({ name: n, type: '物业', s: sg.s, d: sg.d, vpLabel: vp.label, vpCls: vpClsMap[vp.label] || 'ti' })
      ptList.push({
        name: n, desc: v.desc || '', priceStr: lp.toLocaleString(),
        vpLabel: vp.label, vpCls: vpClsMap[vp.label] || 'ti',
        tempLabel: tp.l, tempScore: tp.s, tempCls: tp.c,
        rentYield: v.rentYield, monthsOfSupply: v.monthsOfSupply,
        premiumRate: (v.premiumRate * 100).toFixed(0), signals: sg.s,
        changes: [
          { label: '月', val: fmt.fc(mc), cls: fmt.vcClass(mc) },
          { label: '3月', val: fmt.fc(m3), cls: fmt.vcClass(m3) },
          { label: '年', val: fmt.fc(yc), cls: fmt.vcClass(yc) }
        ]
      })
    })

    var tt = names.length
    var upPct = tt ? Math.round(upCount / tt * 100) : 0
    var insightText = tt + '类物业中' + upCount + '类年涨(' + upPct + '%)，'
    insightText += upPct >= 60 ? '多数物业向好，市场回暖面较广' :
      upPct >= 30 ? '结构分化明显，部分品类先行企稳' : '普跌格局未改，仅个别品类抗跌'

    this.setData({
      ptList: ptList,
      ptInsight: { text: insightText, cls: upPct >= 60 ? 'tp' : upPct >= 30 ? 'tn' : 'tng' }
    })
    this._rebuildSignalDisplay()
  },

  _buildHotZones: function(hzRaw) {
    var list = []
    var targets = this._signalTargets

    Object.keys(hzRaw).forEach(function(n) {
      var v = hzRaw[n]
      var p = v.prices || [], vol = v.volumes || []
      if (p.length < 3) return
      var lp = p[p.length - 1]
      var yc = algo.cC(p, 12), m3c = algo.cC(p, 3)
      var sg = algo.dSg(p, vol)
      var vp = algo.vpDx(p, vol)
      var vpClsMap2 = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }
      targets.push({ name: n, type: '板块', s: sg.s, d: sg.d, vpLabel: vp.label, vpCls: vpClsMap2[vp.label] || 'ti' })
      list.push({
        name: n, sub: v.sub || v.district || '', district: v.district || '',
        price: lp, priceStr: lp.toLocaleString(),
        yc: yc, ycStr: fmt.fc(yc), ycCls: fmt.vcClass(yc),
        m3c: m3c, m3Str: fmt.fc(m3c), m3Cls: fmt.vcClass(m3c),
        barW: 0, signals: sg.s,
        rentYield: v.rentYield || 0
      })
    })

    list.sort(function(a, b) { return b.price - a.price })
    this._hzAll = list

    var districtSet = {}
    list.forEach(function(h) { if (h.district) districtSet[h.district] = true })
    var districtList = ['全部'].concat(Object.keys(districtSet).sort())
    var showFilter = Object.keys(districtSet).length > 1 && list.length > 10

    var display = list.slice(0, 30)
    var maxAbs = 0
    display.forEach(function(h) { if (Math.abs(h.m3c) > maxAbs) maxAbs = Math.abs(h.m3c) })
    if (maxAbs === 0) maxAbs = 1
    display.forEach(function(h) { h.barW = Math.min(100, Math.abs(h.m3c) / maxAbs * 100).toFixed(0) })

    var upCount = 0
    list.forEach(function(h) { if (h.yc > 0) upCount++ })
    var total = list.length
    var upPct = total ? Math.round(upCount / total * 100) : 0
    var insightText = (total > 30 ? '展示前30/' : '共') + total + '个板块，' + upCount + '个年涨(' + upPct + '%)。'
    insightText += upPct >= 50 ? '多数板块回暖，市场底部较为扎实' :
      upPct >= 25 ? '板块分化显著，核心板块率先企稳' : '普跌态势延续，仅极少数板块抗跌'

    this.setData({
      hzList: display,
      hzInsight: { text: insightText, cls: upPct >= 50 ? 'tp' : upPct >= 25 ? 'tn' : 'tng' },
      hzDistricts: districtList,
      hzDistrictIdx: 0,
      hzShowFilter: showFilter,
      hzSort: 'price'
    })
    this._rebuildSignalDisplay()
  },

  _buildAreaRings: function(arRaw) {
    var list = []
    var maxPrice = 0

    Object.keys(arRaw).forEach(function(n) {
      var v = arRaw[n]
      var p = v.prices || []
      if (p.length < 2) return
      var lp = p[p.length - 1]
      if (lp > maxPrice) maxPrice = lp
      list.push({
        name: n, desc: v.desc || '', price: lp, priceStr: lp.toLocaleString(),
        rentYield: v.rentYield, monthsOfSupply: v.monthsOfSupply,
        premiumRate: (v.premiumRate * 100).toFixed(0),
        yc: algo.cC(p, 12), mc: algo.cC(p, 1)
      })
    })

    list.sort(function(a, b) { return b.price - a.price })
    if (maxPrice === 0) maxPrice = 1
    list.forEach(function(a) {
      a.barW = Math.round(a.price / maxPrice * 100)
      a.ycStr = fmt.fc(a.yc); a.ycCls = fmt.vcClass(a.yc)
      a.mcStr = fmt.fc(a.mc); a.mcCls = fmt.vcClass(a.mc)
    })

    var spread = list.length >= 2 ? ((list[0].price - list[list.length - 1].price) / list[list.length - 1].price * 100).toFixed(0) : 0
    var coreYc = list.length ? list[0].yc : 0
    var outerYc = list.length >= 2 ? list[list.length - 1].yc : 0
    var insightText = '价格梯度' + spread + '%，'
    insightText += coreYc > outerYc + 2 ? '核心区领涨，资金回流核心资产' :
      outerYc > coreYc + 2 ? '外围涨幅更大，存在补涨或价值洼地效应' : '各环线涨跌幅相近，整体同步'

    this.setData({
      arList: list,
      arInsight: { text: insightText, cls: coreYc > 0 && outerYc > 0 ? 'tp' : coreYc > 0 || outerYc > 0 ? 'tn' : 'tng' }
    })
  },

  // Chart
  onTrendChartInit: function(e) {
    this._trendChartDetail = e.detail
    this._drawTrendIfReady()
  },

  _drawTrendIfReady: function() {
    var detail = this._trendChartDetail
    if (!detail || !this._cityData) return
    var ctx = detail.ctx, w = detail.width, h = detail.height
    var g = app.globalData
    var d = this._cityData, nat = g.national
    var n = PERIOD_MAP[this.data.trendPeriod] || 13
    var months = fmt.monthsShort(g.meta.months).slice(-n)
    var cityBc = fmt.baselineChange(d.prices.slice(-n))
    var natBc = fmt.baselineChange(nat.prices.slice(-n))

    var allVals = natBc.concat(cityBc)
    var minV = Math.min.apply(null, allVals), maxV = Math.max.apply(null, allVals)
    var range = maxV - minV || 1
    var padL = 40, padR = 10, padT = 20, padB = 30
    var cw = w - padL - padR, ch = h - padT - padB

    function toX(i) { return padL + (i / (months.length - 1)) * cw }
    function toY(v) { return padT + (1 - (v - minV) / range) * ch }

    ctx.clearRect(0, 0, w, h)
    ctx.strokeStyle = '#f0f0f0'; ctx.lineWidth = 0.5
    for (var i = 0; i < 5; i++) {
      var yy = padT + (ch / 4) * i
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(w - padR, yy); ctx.stroke()
    }
    ctx.fillStyle = '#999'; ctx.font = '9px sans-serif'; ctx.textAlign = 'center'
    var step = months.length > 13 ? 3 : 2
    for (var j = 0; j < months.length; j += step) ctx.fillText(months[j], toX(j), h - 8)
    ctx.textAlign = 'right'
    for (var k = 0; k < 5; k++) {
      var val = minV + (range / 4) * (4 - k)
      ctx.fillText((val > 0 ? '+' : '') + val.toFixed(1) + '%', padL - 4, padT + (ch / 4) * k + 3)
    }

    function drawLine(data, color, width, dash) {
      ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash || [])
      ctx.beginPath()
      for (var i = 0; i < data.length; i++) {
        var x = toX(i), y = toY(data[i])
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
      }
      ctx.stroke(); ctx.setLineDash([])
    }

    drawLine(natBc, '#aaa', 1.5, [4, 2])
    drawLine(cityBc, '#2980b9', 2.5)

    ctx.font = '10px sans-serif'; ctx.textAlign = 'left'
    ctx.fillStyle = '#2980b9'; ctx.fillText(this.data.cityName, padL + 4, padT - 4)
    ctx.fillStyle = '#aaa'; ctx.fillText('全国', padL + 50, padT - 4)
  },

  switchTrendPeriod: function(e) {
    var p = e.currentTarget.dataset.p
    if (p === this.data.trendPeriod) return
    this.setData({ trendPeriod: p })
    this._drawTrendIfReady()
  },

  switchTab: function(e) {
    this.setData({ activeTab: e.currentTarget.dataset.tab })
  },

  toggleInactive: function() {
    this.setData({ showInactive: !this.data.showInactive })
  },

  switchHzSort: function(e) {
    var sort = e.currentTarget.dataset.sort
    if (sort === this.data.hzSort) return
    this.setData({ hzSort: sort })
    this._applyHzFilter()
  },

  switchHzDistrict: function(e) {
    var idx = parseInt(e.currentTarget.dataset.idx)
    if (idx === this.data.hzDistrictIdx) return
    this.setData({ hzDistrictIdx: idx })
    this._applyHzFilter()
  },

  _applyHzFilter: function() {
    var all = this._hzAll || []
    var districts = this.data.hzDistricts || []
    var idx = this.data.hzDistrictIdx || 0
    var sort = this.data.hzSort || 'price'

    var filtered = all
    if (idx > 0 && districts[idx]) {
      var target = districts[idx]
      filtered = all.filter(function(h) { return h.district === target })
    }

    var sorted = filtered.slice()
    if (sort === 'change') {
      sorted.sort(function(a, b) { return b.yc - a.yc })
    } else if (sort === 'rent') {
      sorted.sort(function(a, b) { return (b.rentYield || 0) - (a.rentYield || 0) })
    } else {
      sorted.sort(function(a, b) { return b.price - a.price })
    }

    var display = sorted.slice(0, 30)
    var maxAbs = 0
    display.forEach(function(h) { if (Math.abs(h.m3c) > maxAbs) maxAbs = Math.abs(h.m3c) })
    if (maxAbs === 0) maxAbs = 1
    display.forEach(function(h) { h.barW = Math.min(100, Math.abs(h.m3c) / maxAbs * 100).toFixed(0) })

    this.setData({ hzList: display })
  },

  onShareAppMessage: function() {
    return {
      title: this.data.cityName + ' — 房产趋势看板',
      path: '/pages/citytab/index'
    }
  }
})
