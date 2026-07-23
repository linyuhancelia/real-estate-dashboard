var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var app = getApp()

Page({
  data: {
    loaded: false,
    activeTab: 'rs',
    rsList: [],
    ryList: [],
    mssList: [],
    favCities: []
  },

  onLoad: function() {
    this._loadFav()
    var self = this
    app.onDataReady(function() {
      self.buildRankings()
    })
  },

  onShow: function() {
    this._loadFav()
    if (app.globalData.loaded && !this.data.loaded) {
      this.buildRankings()
    } else if (this.data.loaded) {
      this._markFav()
    }
  },

  _loadFav: function() {
    try {
      var fav = wx.getStorageSync('fav_cities') || []
      this.setData({ favCities: fav })
    } catch (e) {}
  },

  _markFav: function() {
    var favSet = {}
    this.data.favCities.forEach(function(n) { favSet[n] = true })
    function mark(list) {
      return list.map(function(it) {
        it.isFav = !!favSet[it.name]
        return it
      })
    }
    this.setData({
      rsList: mark(this.data.rsList),
      ryList: mark(this.data.ryList),
      mssList: mark(this.data.mssList)
    })
  },

  buildRankings: function() {
    var g = app.globalData
    var cities = g.cities
    var allPrices = g.allPrices
    var natPrices = g.national.prices
    var favSet = {}
    this.data.favCities.forEach(function(n) { favSet[n] = true })

    var items = Object.keys(cities).filter(function(name) {
      return algo.isReliable(cities[name].prices)
    }).map(function(name) {
      var c = cities[name]
      var rs = algo.cRS(c.prices, allPrices, natPrices)
      var yc = algo.cC(c.prices, 12)
      return {
        name: name,
        tier: c.tier,
        province: c.province,
        price: c.prices[c.prices.length - 1],
        priceStr: c.prices[c.prices.length - 1].toLocaleString(),
        rs: rs,
        yc: yc,
        ycStr: fmt.fc(yc),
        ycCls: fmt.vcClass(yc),
        rentYield: c.rentYield || 0,
        monthsOfSupply: c.monthsOfSupply || 0,
        isFav: !!favSet[name]
      }
    })

    function copyItems(arr) {
      return arr.map(function(it) {
        return {
          name: it.name, tier: it.tier, province: it.province,
          price: it.price, priceStr: it.priceStr, rs: it.rs,
          yc: it.yc, ycStr: it.ycStr, ycCls: it.ycCls,
          rentYield: it.rentYield, monthsOfSupply: it.monthsOfSupply,
          isFav: it.isFav
        }
      })
    }

    var rsList = copyItems(items).sort(function(a, b) { return b.rs - a.rs })
    rsList.forEach(function(it, i) {
      it.rank = i + 1
      it.val = it.rs.toString()
      it.valColor = it.rs >= 60 ? '#2d8c4e' : it.rs >= 40 ? '#e67e22' : '#c0392b'
    })

    var ryList = copyItems(items).sort(function(a, b) { return b.rentYield - a.rentYield })
    ryList.forEach(function(it, i) {
      it.rank = i + 1
      it.val = it.rentYield + '%'
      it.valColor = it.rentYield >= 3 ? '#2d8c4e' : it.rentYield >= 2 ? '#e67e22' : '#c0392b'
    })

    var mssList = copyItems(items).sort(function(a, b) { return a.monthsOfSupply - b.monthsOfSupply })
    mssList.forEach(function(it, i) {
      it.rank = i + 1
      it.val = it.monthsOfSupply + '月'
      it.valColor = it.monthsOfSupply <= 12 ? '#2d8c4e' : it.monthsOfSupply <= 18 ? '#e67e22' : '#c0392b'
    })

    this.setData({
      loaded: true,
      rsList: rsList,
      ryList: ryList,
      mssList: mssList
    })
  },

  switchTab: function(e) {
    this.setData({ activeTab: e.currentTarget.dataset.tab })
  },

  onCityTap: function(e) {
    var name = e.currentTarget.dataset.name
    wx.navigateTo({ url: '/pages/city/index?name=' + encodeURIComponent(name) })
  },

  onShareAppMessage: function() {
    return {
      title: '城市排行榜 — 房产趋势看板',
      path: '/pages/rankings/index'
    }
  }
})
