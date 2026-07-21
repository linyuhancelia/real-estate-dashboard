var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var dataService = require('../../utils/data')
var app = getApp()

var PERIOD_MAP = { '6月': 7, '1年': 13, '2年': 25 }

Page({
  data: {
    loaded: false,
    detailLoaded: false,
    trendPeriod: '1年',
    vpPeriod: '1年',
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
    activeTab: 'property',
    signalTargets: [],
    inactiveSignals: [],
    inactiveCount: 0,
    showInactive: false,
    sigSummary: {},
    ptList: [],
    ptInsight: null,
    hzList: [],
    hzInsight: null,
    hzSort: 'price',
    arList: [],
    arInsight: null,
    vpDiag: null,
    vpTable: []
  },

  onLoad: function(options) {
    var name = decodeURIComponent(options.name || '上海')
    this._cityName = name
    wx.setNavigationBarTitle({ title: name })

    var self = this
    app.onDataReady(function() {
      self.initProfile(name)
    })
  },

  initProfile: function(name) {
    var g = app.globalData
    var d = g.cities[name]
    if (!d) return

    var lp = d.prices[d.prices.length - 1]
    var wc = algo.cC(d.prices, 1) / 4
    var mc = algo.cC(d.prices, 1)
    var m3 = algo.cC(d.prices, 3)
    var yc = algo.cC(d.prices, 12)

    var tp = algo.cTp(d.prices, d.volumes)
    var rs = algo.cRS(d.prices, g.allPrices, g.national.prices)
    var sg = algo.dSg(d.prices, d.volumes)
    var judge = algo.mktJudge(d.prices, d.volumes)

    this.setData({
      loaded: true,
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
      judge: judge
    })

    var vp = algo.vpDx(d.prices, d.volumes)
    var vpClsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }
    this.setData({ vpDiag: { label: vp.label, cls: vpClsMap[vp.label] || 'ti' } })

    this._cityData = d
    this._natData = g.national
    this.buildSignals(name, d)
    this.buildVolPrice(d, g.meta)
    this.loadDetail(name)
  },

  buildSignals: function(name, d) {
    var vpClsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }
    var targets = [{ name: name + '(整体)', type: '城市', p: d.prices, v: d.volumes }]

    var onC = 0, stC = 0, rcC = 0
    var signalTargets = targets.map(function(t) {
      var r = algo.dSg(t.p, t.v)
      var vp = algo.vpDx(t.p, t.v)
      if (r.s.sd) onC++
      if (r.s.st) stC++
      if (r.s.rc) rcC++
      return { name: t.name, type: t.type, s: r.s, d: r.d, vpLabel: vp.label, vpCls: vpClsMap[vp.label] || 'ti' }
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
      signalTargets: signalTargets.filter(function(t) {
        return t.s.sd || t.s.st || t.s.rc
      }),
      inactiveSignals: signalTargets.filter(function(t) {
        return !t.s.sd && !t.s.st && !t.s.rc
      }),
      inactiveCount: signalTargets.filter(function(t) {
        return !t.s.sd && !t.s.st && !t.s.rc
      }).length,
      showInactive: false,
      sigSummary: { text: text, verdict: verdict, cls: cls }
    })
  },

  buildVolPrice: function(d, meta) {
    var vp = algo.vpDx(d.prices, d.volumes)
    var clsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }
    this.setData({
      vpDiag: {
        label: vp.label,
        detail: vp.detail,
        hint: vp.hint,
        cls: clsMap[vp.label] || 'ti'
      }
    })

    var months = fmt.monthsShort(meta.months)
    var ps = d.prices
    var vs = d.volumes
    var len = Math.min(6, ps.length)
    var table = []
    for (var i = ps.length - len; i < ps.length; i++) {
      var pc = i > 0 ? (ps[i] - ps[i - 1]) / ps[i - 1] * 100 : 0
      var vc = i > 0 && vs[i - 1] > 0 ? (vs[i] - vs[i - 1]) / vs[i - 1] * 100 : 0
      table.push({
        month: months[i] || '',
        price: ps[i].toLocaleString(),
        pc: fmt.fc(pc),
        pcCls: fmt.vcClass(pc),
        vol: vs[i].toLocaleString(),
        vc: fmt.fc(vc),
        vcCls: fmt.vcClass(vc)
      })
    }
    this.setData({ vpTable: table })

    this._vpData = { prices: ps, volumes: vs, months: months }
  },

  loadDetail: function(name) {
    var self = this
    dataService.loadCityDetail(name).then(function(detail) {
      self._detail = detail

      var currentTargets = self.data.signalTargets.slice()

      if (detail.property_types) {
        self.buildPropertyTypes(detail.property_types, currentTargets)
        currentTargets = self.data.signalTargets.slice()
      }

      if (detail.hot_zones) {
        self.buildHotZones(detail.hot_zones, currentTargets)
        currentTargets = self.data.signalTargets.slice()
      }

      if (detail.area_rings) {
        self.buildAreaRings(detail.area_rings)
      }

      self.setData({ detailLoaded: true })
    }).catch(function(err) {
      console.error('[city] loadDetail failed:', err)
      self.setData({ detailLoaded: true })
    })
  },

  buildPropertyTypes: function(pts, currentTargets) {
    var ptList = []
    var upCount = 0
    var names = Object.keys(pts)

    names.forEach(function(n) {
      var v = pts[n]
      var p = v.prices
      var vol = v.volumes
      var lp = p[p.length - 1]
      var mc = algo.cC(p, 1)
      var m3 = algo.cC(p, 3)
      var yc = algo.cC(p, 12)
      var tp = algo.cTp(p, vol)
      var sg = algo.dSg(p, vol)
      var vp = algo.vpDx(p, vol)
      var vpClsMap = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }

      if (yc > 0) upCount++

      currentTargets.push({ name: n, type: '物业', s: sg.s, d: sg.d, vpLabel: vp.label, vpCls: vpClsMap[vp.label] || 'ti' })

      ptList.push({
        name: n,
        desc: v.desc || '',
        priceStr: lp.toLocaleString(),
        vpLabel: vp.label,
        vpCls: vpClsMap[vp.label] || 'ti',
        tempLabel: tp.l,
        tempScore: tp.s,
        tempCls: tp.c,
        rentYield: v.rentYield,
        monthsOfSupply: v.monthsOfSupply,
        premiumRate: (v.premiumRate * 100).toFixed(0),
        signals: sg.s,
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
    if (upPct >= 60) {
      insightText += '多数物业向好，市场回暖面较广'
    } else if (upPct >= 30) {
      insightText += '结构分化明显，部分品类先行企稳'
    } else {
      insightText += '普跌格局未改，仅个别品类抗跌'
    }
    var insCls = upPct >= 60 ? 'tp' : upPct >= 30 ? 'tn' : 'tng'

    this.setData({
      ptList: ptList,
      ptInsight: { text: insightText, cls: insCls },
      signalTargets: currentTargets
    })
    this.rebuildSigSummary(currentTargets)
  },

  buildHotZones: function(hzRaw, currentTargets) {
    var list = []
    var maxPrice = 0

    Object.keys(hzRaw).forEach(function(n) {
      var v = hzRaw[n]
      var p = v.prices || []
      var vol = v.volumes || []
      if (p.length < 3) return
      var lp = p[p.length - 1]
      if (lp > maxPrice) maxPrice = lp
      var yc = algo.cC(p, 12)
      var m3c = algo.cC(p, 3)
      var sg = algo.dSg(p, vol)
      var vp = algo.vpDx(p, vol)
      var vpClsMap2 = { '量价齐升': 'tp', '价升量缩': 'tw', '量升价跌': 'tn', '量价齐跌': 'tng', '缩量盘整': 'ti' }

      currentTargets.push({ name: n, type: '板块', s: sg.s, d: sg.d, vpLabel: vp.label, vpCls: vpClsMap2[vp.label] || 'ti' })

      list.push({
        name: n,
        sub: v.sub || v.district || '',
        district: v.district || '',
        price: lp,
        priceStr: lp.toLocaleString(),
        yc: yc,
        ycStr: fmt.fc(yc),
        ycCls: fmt.vcClass(yc),
        m3c: m3c,
        m3Str: fmt.fc(m3c),
        m3Cls: fmt.vcClass(m3c),
        barW: 0,
        signals: sg.s
      })
    })

    list.sort(function(a, b) { return b.price - a.price })
    var top = list.slice(0, 30)
    var maxAbs = 0
    top.forEach(function(h) { if (Math.abs(h.m3c) > maxAbs) maxAbs = Math.abs(h.m3c) })
    if (maxAbs === 0) maxAbs = 1
    top.forEach(function(h) { h.barW = Math.min(100, Math.abs(h.m3c) / maxAbs * 100).toFixed(0) })

    this._hzAll = top
    this._hzMaxAbs = maxAbs

    var upCount = 0
    top.forEach(function(h) { if (h.yc > 0) upCount++ })
    var upPct = top.length ? Math.round(upCount / top.length * 100) : 0
    var insightText = '展示前' + top.length + '个板块，' + upCount + '个年涨(' + upPct + '%)。'
    if (upPct >= 50) {
      insightText += '多数板块回暖，市场底部较为扎实'
    } else if (upPct >= 25) {
      insightText += '板块分化显著，核心板块率先企稳'
    } else {
      insightText += '普跌态势延续，仅极少数板块抗跌'
    }
    var insCls = upPct >= 50 ? 'tp' : upPct >= 25 ? 'tn' : 'tng'

    this.setData({
      hzList: top,
      hzInsight: { text: insightText, cls: insCls },
      signalTargets: currentTargets
    })
    this.rebuildSigSummary(currentTargets)
  },

  buildAreaRings: function(arRaw) {
    var list = []
    var maxPrice = 0

    Object.keys(arRaw).forEach(function(n) {
      var v = arRaw[n]
      var p = v.prices || []
      if (p.length < 2) return
      var lp = p[p.length - 1]
      if (lp > maxPrice) maxPrice = lp
      list.push({
        name: n,
        desc: v.desc || '',
        price: lp,
        priceStr: lp.toLocaleString(),
        rentYield: v.rentYield,
        monthsOfSupply: v.monthsOfSupply,
        premiumRate: (v.premiumRate * 100).toFixed(0),
        yc: algo.cC(p, 12),
        mc: algo.cC(p, 1)
      })
    })

    list.sort(function(a, b) { return b.price - a.price })

    if (maxPrice === 0) maxPrice = 1
    list.forEach(function(a) {
      a.barW = Math.round(a.price / maxPrice * 100)
      a.ycStr = fmt.fc(a.yc)
      a.ycCls = fmt.vcClass(a.yc)
      a.mcStr = fmt.fc(a.mc)
      a.mcCls = fmt.vcClass(a.mc)
    })

    var spread = list.length >= 2 ? ((list[0].price - list[list.length - 1].price) / list[list.length - 1].price * 100).toFixed(0) : 0
    var coreYc = list.length ? list[0].yc : 0
    var outerYc = list.length >= 2 ? list[list.length - 1].yc : 0
    var insightText = '价格梯度' + spread + '%，'
    if (coreYc > outerYc + 2) {
      insightText += '核心区领涨，资金回流核心资产'
    } else if (outerYc > coreYc + 2) {
      insightText += '外围涨幅更大，存在补涨或价值洼地效应'
    } else {
      insightText += '各环线涨跌幅相近，整体同步'
    }
    var insCls = coreYc > 0 && outerYc > 0 ? 'tp' : coreYc > 0 || outerYc > 0 ? 'tn' : 'tng'

    this.setData({
      arList: list,
      arInsight: { text: insightText, cls: insCls }
    })
  },

  rebuildSigSummary: function(targets) {
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
    this.setData({ sigSummary: { text: text, verdict: verdict, cls: cls } })
  },

  onCityChartInit: function(e) {
    this._trendChartDetail = e.detail
    this._drawTrendChartFromData()
  },

  _drawTrendChartFromData: function() {
    var detail = this._trendChartDetail
    if (!detail) return
    var ctx = detail.ctx
    var w = detail.width
    var h = detail.height
    var g = app.globalData
    var d = this._cityData
    var nat = g.national

    if (!d || !nat) return

    var n = PERIOD_MAP[this.data.trendPeriod] || 13
    var months = fmt.monthsShort(g.meta.months).slice(-n)
    var cityBc = fmt.baselineChange(d.prices.slice(-n))
    var natBc = fmt.baselineChange(nat.prices.slice(-n))

    this._drawTrendChart(ctx, w, h, months, [
      { data: natBc, color: '#aaa', width: 1.5, dash: [4, 2], label: '全国' },
      { data: cityBc, color: '#2980b9', width: 2.5, label: this._cityName }
    ])
  },

  onVpChartInit: function(e) {
    this._vpChartDetail = e.detail
    this._drawVpChartFromData()
  },

  _drawVpChartFromData: function() {
    var detail = this._vpChartDetail
    if (!detail) return
    var ctx = detail.ctx
    var w = detail.width
    var h = detail.height

    if (!this._vpData) return

    var n = PERIOD_MAP[this.data.vpPeriod] || 13
    var vd = this._vpData
    var ps = vd.prices.slice(-n)
    var vs = vd.volumes.slice(-n)
    var months = vd.months.slice(-n)

    var pMin = Math.min.apply(null, ps)
    var pMax = Math.max.apply(null, ps)
    var pRange = pMax - pMin || 1
    var vMax = Math.max.apply(null, vs) || 1

    var padL = 45, padR = 45, padT = 25, padB = 30
    var cw = w - padL - padR
    var ch = h - padT - padB

    ctx.clearRect(0, 0, w, h)

    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 0.5
    for (var i = 0; i < 5; i++) {
      var yy = padT + (ch / 4) * i
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(w - padR, yy); ctx.stroke()
    }

    var barW = cw / months.length * 0.6
    ctx.fillStyle = 'rgba(41,128,185,0.25)'
    for (var j = 0; j < vs.length; j++) {
      var bx = padL + (j + 0.5) / months.length * cw - barW / 2
      var bh = (vs[j] / vMax) * ch
      var by = padT + ch - bh
      ctx.fillRect(bx, by, barW, bh)
    }

    ctx.strokeStyle = '#e74c3c'
    ctx.lineWidth = 2.5
    ctx.beginPath()
    for (var k = 0; k < ps.length; k++) {
      var px = padL + (k + 0.5) / months.length * cw
      var py = padT + (1 - (ps[k] - pMin) / pRange) * ch
      if (k === 0) ctx.moveTo(px, py)
      else ctx.lineTo(px, py)
    }
    ctx.stroke()

    ctx.fillStyle = '#999'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'center'
    for (var m = 0; m < months.length; m += 2) {
      ctx.fillText(months[m], padL + (m + 0.5) / months.length * cw, h - 8)
    }

    ctx.textAlign = 'right'
    ctx.fillStyle = '#e74c3c'
    for (var n = 0; n < 5; n++) {
      var pv = pMin + (pRange / 4) * (4 - n)
      ctx.fillText(Math.round(pv).toLocaleString(), padL - 4, padT + (ch / 4) * n + 3)
    }

    ctx.textAlign = 'left'
    ctx.fillStyle = '#2980b9'
    for (var q = 0; q < 5; q++) {
      var vv = Math.round(vMax / 4 * (4 - q))
      ctx.fillText(vv.toLocaleString(), w - padR + 4, padT + (ch / 4) * q + 3)
    }

    ctx.font = '10px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillStyle = '#e74c3c'
    ctx.fillText('均价', padL, padT - 8)
    ctx.fillStyle = '#2980b9'
    ctx.fillText('成交量', padL + 40, padT - 8)
  },

  _drawTrendChart: function(ctx, w, h, months, series) {
    var allVals = []
    series.forEach(function(s) { allVals = allVals.concat(s.data) })
    var minV = Math.min.apply(null, allVals)
    var maxV = Math.max.apply(null, allVals)
    var range = maxV - minV || 1

    var padL = 40, padR = 10, padT = 20, padB = 30
    var cw = w - padL - padR
    var ch = h - padT - padB

    function toX(i) { return padL + (i / (months.length - 1)) * cw }
    function toY(v) { return padT + (1 - (v - minV) / range) * ch }

    ctx.clearRect(0, 0, w, h)

    ctx.strokeStyle = '#f0f0f0'
    ctx.lineWidth = 0.5
    for (var i = 0; i < 5; i++) {
      var yy = padT + (ch / 4) * i
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(w - padR, yy); ctx.stroke()
    }

    ctx.fillStyle = '#999'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'center'
    var step = months.length > 13 ? 3 : 2
    for (var j = 0; j < months.length; j += step) {
      ctx.fillText(months[j], toX(j), h - 8)
    }

    ctx.textAlign = 'right'
    for (var k = 0; k < 5; k++) {
      var val = minV + (range / 4) * (4 - k)
      ctx.fillText((val > 0 ? '+' : '') + val.toFixed(1) + '%', padL - 4, padT + (ch / 4) * k + 3)
    }

    series.forEach(function(s) {
      ctx.strokeStyle = s.color
      ctx.lineWidth = s.width
      ctx.setLineDash(s.dash || [])
      ctx.beginPath()
      for (var i = 0; i < s.data.length; i++) {
        var x = toX(i), y = toY(s.data[i])
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
      ctx.setLineDash([])
    })

    ctx.font = '10px sans-serif'
    ctx.textAlign = 'left'
    var lx = padL + 4
    series.forEach(function(s) {
      if (s.label) {
        ctx.fillStyle = s.color
        ctx.fillText(s.label, lx, padT - 4)
        lx += ctx.measureText(s.label).width + 12
      }
    })
  },

  switchTab: function(e) {
    var tab = e.currentTarget.dataset.tab
    this.setData({ activeTab: tab })
  },

  toggleInactive: function() {
    this.setData({ showInactive: !this.data.showInactive })
  },

  switchTrendPeriod: function(e) {
    var p = e.currentTarget.dataset.p
    if (p === this.data.trendPeriod) return
    this.setData({ trendPeriod: p })
    this._drawTrendChartFromData()
  },

  switchVpPeriod: function(e) {
    var p = e.currentTarget.dataset.p
    if (p === this.data.vpPeriod) return
    this.setData({ vpPeriod: p })
    this._drawVpChartFromData()
    this._rebuildVpTable()
  },

  _rebuildVpTable: function() {
    if (!this._vpData) return
    var n = PERIOD_MAP[this.data.vpPeriod] || 13
    var vd = this._vpData
    var ps = vd.prices.slice(-n)
    var vs = vd.volumes.slice(-n)
    var months = vd.months.slice(-n)
    var table = []
    for (var i = 0; i < ps.length; i++) {
      var pc = i > 0 ? (ps[i] - ps[i - 1]) / ps[i - 1] * 100 : 0
      var vc = i > 0 && vs[i - 1] > 0 ? (vs[i] - vs[i - 1]) / vs[i - 1] * 100 : 0
      table.push({
        month: months[i] || '',
        price: ps[i].toLocaleString(),
        pc: fmt.fc(pc),
        pcCls: fmt.vcClass(pc),
        vol: vs[i].toLocaleString(),
        vc: fmt.fc(vc),
        vcCls: fmt.vcClass(vc)
      })
    }
    this.setData({ vpTable: table })
  },

  switchHzSort: function(e) {
    var sort = e.currentTarget.dataset.sort
    if (sort === this.data.hzSort) return
    var list = this._hzAll ? this._hzAll.slice() : []
    if (sort === 'change') {
      list.sort(function(a, b) { return b.yc - a.yc })
    } else if (sort === 'rent') {
      list.sort(function(a, b) { return b.rentYield - a.rentYield })
    } else {
      list.sort(function(a, b) { return b.price - a.price })
    }
    this.setData({ hzSort: sort, hzList: list })
  },

  onShareAppMessage: function() {
    var j = this.data.judge
    return {
      title: this._cityName + ' — ' + (j.verdict || '房产趋势看板'),
      path: '/pages/city/index?name=' + encodeURIComponent(this._cityName)
    }
  }
})
