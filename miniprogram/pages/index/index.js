var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var app = getApp()

var PERIOD_MAP = { '6月': 7, '1年': 13, '2年': 25 }

Page({
  data: {
    loaded: false,
    updateTime: '',
    natJudge: {},
    shJudge: {},
    shVsNat: '',
    tierCards: [],
    period: '1年'
  },

  onLoad: function() {
    var self = this
    app.onDataReady(function() {
      self.initPage()
    })
  },

  onShow: function() {
    if (app.globalData.loaded && !this.data.loaded) {
      this.initPage()
    }
  },

  initPage: function() {
    var g = app.globalData
    var nat = g.national
    var cities = g.cities
    var sh = cities['上海']

    var natJudge = algo.mktJudge(nat.prices, nat.volumes)
    var shJudge = sh ? algo.mktJudge(sh.prices, sh.volumes) : { verdict: '—', cls: 'ti', detail: '', hint: '' }

    var nyc = algo.cC(nat.prices, 12)
    var syc = sh ? algo.cC(sh.prices, 12) : 0
    var diff = Math.abs(syc - nyc).toFixed(1)
    var shVsNat = (syc > nyc ? '跑赢' : '跑输') + '全国' + diff + 'pp'

    this.setData({
      loaded: true,
      updateTime: g.meta.generated_at || '',
      natJudge: natJudge,
      shJudge: shJudge,
      shVsNat: shVsNat
    })

    this.buildTierCards(cities)
  },

  buildTierCards: function(cities) {
    var tierMap = {}

    Object.keys(cities).forEach(function(name) {
      var c = cities[name]
      var tier = c.tier
      if (!tierMap[tier]) tierMap[tier] = []
      var yc = algo.cC(c.prices, 12)
      var tp = algo.cTp(c.prices, c.volumes)
      tierMap[tier].push({
        name: name,
        price: c.prices[c.prices.length - 1],
        yc: yc,
        tp: tp,
        absYc: Math.abs(yc)
      })
    })

    var displayOrder = ['一线', '新一线', '二线', '三线', '旅居', '特别行政区']
    var cards = displayOrder.map(function(tier) {
      var list = tierMap[tier] || []
      if (list.length === 0) return null
      var count = list.length
      var avgPrice = Math.round(list.reduce(function(s, c) { return s + c.price }, 0) / count)
      var avgYc = list.reduce(function(s, c) { return s + c.yc }, 0) / count

      list.sort(function(a, b) { return b.absYc - a.absYc })
      var top1 = list[0]

      return {
        tier: tier,
        count: count,
        avgPrice: avgPrice.toLocaleString(),
        avgYcStr: fmt.fc(avgYc),
        avgYcCls: fmt.vcClass(avgYc),
        top1Name: top1.name,
        top1YcStr: fmt.fc(top1.yc),
        top1YcCls: fmt.vcClass(top1.yc),
        top1TempL: top1.tp.l,
        top1TempC: top1.tp.c
      }
    }).filter(Boolean)

    this.setData({ tierCards: cards })
  },

  switchPeriod: function(e) {
    var p = e.currentTarget.dataset.p
    if (p === this.data.period) return
    this.setData({ period: p })
    this._drawChart()
  },

  onOvChartInit: function(e) {
    this._chartDetail = e.detail
    this._drawChart()
  },

  _drawChart: function() {
    var detail = this._chartDetail
    if (!detail) return
    var ctx = detail.ctx
    var w = detail.width
    var h = detail.height
    var g = app.globalData
    var nat = g.national
    var sh = g.cities['上海']
    var meta = g.meta

    if (!nat || !sh) return

    var n = PERIOD_MAP[this.data.period] || 13
    var months = fmt.monthsShort(meta.months).slice(-n)
    var natBc = fmt.baselineChange(nat.prices.slice(-n))
    var shBc = fmt.baselineChange(sh.prices.slice(-n))

    var allVals = natBc.concat(shBc)
    var minV = Math.min.apply(null, allVals)
    var maxV = Math.max.apply(null, allVals)
    var range = maxV - minV || 1

    var padL = 40, padR = 10, padT = 30, padB = 30
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

    function drawLine(data, color, width, dash) {
      ctx.strokeStyle = color
      ctx.lineWidth = width
      ctx.setLineDash(dash || [])
      ctx.beginPath()
      for (var i = 0; i < data.length; i++) {
        var x = toX(i), y = toY(data[i])
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      }
      ctx.stroke()
      ctx.setLineDash([])
    }

    drawLine(natBc, '#999', 1.5, [4, 2])
    drawLine(shBc, '#e74c3c', 2.5)

    ctx.font = '10px sans-serif'
    ctx.fillStyle = '#e74c3c'
    ctx.textAlign = 'left'
    ctx.fillText('上海', padL + 4, padT - 6)
    ctx.fillStyle = '#999'
    ctx.fillText('全国', padL + 40, padT - 6)
  },

  onTop1Tap: function(e) {
    var name = e.currentTarget.dataset.name
    wx.navigateTo({ url: '/pages/city/index?name=' + encodeURIComponent(name) })
  },

  onShareAppMessage: function() {
    return {
      title: '房产趋势看板 — ' + (this.data.natJudge.verdict || '数据驱动购房决策'),
      path: '/pages/index/index'
    }
  }
})
