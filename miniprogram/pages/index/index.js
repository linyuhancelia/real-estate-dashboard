var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var app = getApp()

Page({
  data: {
    loaded: false,
    updateTime: '',
    natJudge: {},
    shJudge: {},
    shVsNat: '',
    provinces: [],
    tiers: [],
    fProv: '',
    fTier: '',
    fSch: '',
    showAll: false,
    filteredCities: [],
    totalCount: 0
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
    var allPrices = g.allPrices

    var natJudge = algo.mktJudge(nat.prices, nat.volumes)
    var shJudge = sh ? algo.mktJudge(sh.prices, sh.volumes) : { verdict: '—', cls: 'ti', detail: '', hint: '' }

    var nyc = algo.cC(nat.prices, 12)
    var syc = sh ? algo.cC(sh.prices, 12) : 0
    var diff = Math.abs(syc - nyc).toFixed(1)
    var shVsNat = (syc > nyc ? '跑赢' : '跑输') + '全国' + diff + 'pp'

    var provinces = [''].concat(g.meta.provinces || [])
    var tiers = [''].concat(g.meta.tiers || [])

    this.setData({
      loaded: true,
      updateTime: g.meta.generated_at || '',
      natJudge: natJudge,
      shJudge: shJudge,
      shVsNat: shVsNat,
      provinces: provinces,
      tiers: tiers
    })

    this._cities = cities
    this._nat = nat
    this._allPrices = allPrices
    this.updateCityList()
  },

  updateCityList: function() {
    var cities = this._cities
    if (!cities) return
    var nat = this._nat
    var allPrices = this._allPrices
    var fProv = this.data.fProv
    var fTier = this.data.fTier
    var fSch = this.data.fSch
    var showAll = this.data.showAll
    var topTiers = { '一线': 1, '新一线': 1 }

    var list = Object.keys(cities).map(function(name) {
      var c = cities[name]
      return {
        name: name,
        tier: c.tier,
        province: c.province,
        prices: c.prices,
        volumes: c.volumes,
        price: c.prices[c.prices.length - 1]
      }
    })

    if (fProv) list = list.filter(function(c) { return c.province === fProv })
    if (fTier) list = list.filter(function(c) { return c.tier === fTier })
    if (fSch) list = list.filter(function(c) { return c.name.indexOf(fSch) >= 0 })

    var totalCount = list.length

    if (!showAll && !fProv && !fTier && !fSch) {
      list = list.filter(function(c) { return topTiers[c.tier] })
    }

    var items = list.map(function(c) {
      var yc = algo.cC(c.prices, 12)
      var tp = algo.cTp(c.prices, c.volumes)
      return {
        name: c.name,
        tier: c.tier,
        province: c.province,
        priceStr: c.price.toLocaleString(),
        ycStr: fmt.fc(yc),
        ycClass: fmt.vcClass(yc),
        tempLabel: tp.l,
        tempScore: tp.s,
        tempClass: tp.c
      }
    })

    this.setData({
      filteredCities: items,
      totalCount: totalCount
    })
  },

  onOvChartInit: function(e) {
    var detail = e.detail
    var ctx = detail.ctx
    var w = detail.width
    var h = detail.height
    var g = app.globalData
    var nat = g.national
    var sh = g.cities['上海']
    var meta = g.meta

    if (!nat || !sh) return

    var months = fmt.monthsShort(meta.months).slice(-13)
    var natBc = fmt.baselineChange(nat.prices.slice(-13))
    var shBc = fmt.baselineChange(sh.prices.slice(-13))

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
    for (var j = 0; j < months.length; j += 2) {
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

  onCityTap: function(e) {
    var name = e.currentTarget.dataset.name
    wx.navigateTo({ url: '/pages/city/index?name=' + encodeURIComponent(name) })
  },

  onProvChange: function(e) {
    this.setData({ fProv: this.data.provinces[e.detail.value] || '', showAll: true })
    this.updateCityList()
  },

  onTierChange: function(e) {
    this.setData({ fTier: this.data.tiers[e.detail.value] || '', showAll: true })
    this.updateCityList()
  },

  onSearch: function(e) {
    this.setData({ fSch: e.detail.value, showAll: true })
    this.updateCityList()
  },

  resetFilter: function() {
    this.setData({ fProv: '', fTier: '', fSch: '', showAll: false })
    this.updateCityList()
  },

  showAllCities: function() {
    this.setData({ showAll: true })
    this.updateCityList()
  },

  onShareAppMessage: function() {
    return {
      title: '房产趋势看板 — ' + (this.data.natJudge.verdict || '数据驱动购房决策'),
      path: '/pages/index/index'
    }
  }
})
