var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var app = getApp()

Page({
  data: {
    loaded: false,
    cityLoaded: false,
    currentCity: '上海',
    searchText: '',
    suggestions: [],
    allCityNames: [],
    favCities: [],
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
    judge: {}
  },

  onLoad: function() {
    this._loadFav()
    var self = this
    app.onDataReady(function() {
      var names = Object.keys(app.globalData.cities).sort()
      self.setData({ loaded: true, allCityNames: names })
      self._selectCity(self.data.currentCity)
    })
  },

  onShow: function() {
    this._loadFav()
    if (app.globalData.loaded && !this.data.loaded) {
      var names = Object.keys(app.globalData.cities).sort()
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
    var name = e.currentTarget.dataset.name
    this._selectCity(name)
  },

  onPickerChange: function(e) {
    var idx = e.detail.value
    var name = this.data.allCityNames[idx]
    if (name) this._selectCity(name)
  },

  onSearch: function(e) {
    var keyword = (e.detail.value || '').trim()
    this.setData({ searchText: keyword })
    if (!keyword) {
      this.setData({ suggestions: [] })
      return
    }
    var results = this.data.allCityNames.filter(function(n) {
      return n.indexOf(keyword) >= 0
    }).slice(0, 8)
    this.setData({ suggestions: results })
  },

  _selectCity: function(name) {
    var g = app.globalData
    var d = g.cities[name]
    if (!d) return

    this.setData({
      searchText: '',
      suggestions: [],
      currentCity: name
    })

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
      judge: judge
    })
  },

  goFullDetail: function() {
    wx.navigateTo({
      url: '/pages/city/index?name=' + encodeURIComponent(this.data.currentCity)
    })
  },

  onShareAppMessage: function() {
    return {
      title: this.data.cityName + ' — 房产趋势看板',
      path: '/pages/citytab/index'
    }
  }
})
