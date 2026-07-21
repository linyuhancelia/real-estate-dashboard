var algo = require('../../utils/algorithms')
var fmt = require('../../utils/format')
var dataService = require('../../utils/data')
var app = getApp()

var MAX_FAV = 5

Page({
  data: {
    loaded: false,
    favCities: [],
    favDetails: [],
    updateTime: '',
    cityCount: 0,
    cacheSize: '',
    showMethod: true,
    allCityNames: []
  },

  onLoad: function() {
    var self = this
    app.onDataReady(function() {
      self.initPage()
    })
  },

  onShow: function() {
    this._loadFav()
    if (app.globalData.loaded) {
      this._buildFavDetails()
    }
  },

  initPage: function() {
    var g = app.globalData
    this.setData({
      loaded: true,
      updateTime: g.meta.generated_at || '',
      cityCount: Object.keys(g.cities).length,
      allCityNames: Object.keys(g.cities).sort()
    })
    this._loadFav()
    this._buildFavDetails()
    this._calcCacheSize()
  },

  _loadFav: function() {
    try {
      var fav = wx.getStorageSync('fav_cities') || []
      this.setData({ favCities: fav })
    } catch (e) {}
  },

  _saveFav: function(fav) {
    try {
      wx.setStorageSync('fav_cities', fav)
      this.setData({ favCities: fav })
    } catch (e) {}
  },

  _buildFavDetails: function() {
    var g = app.globalData
    if (!g.loaded) return
    var cities = g.cities
    var allPrices = g.allPrices
    var natPrices = g.national.prices
    var fav = this.data.favCities

    var details = fav.map(function(name) {
      var c = cities[name]
      if (!c) return null
      var lp = c.prices[c.prices.length - 1]
      var yc = algo.cC(c.prices, 12)
      var tp = algo.cTp(c.prices, c.volumes)
      var rs = algo.cRS(c.prices, allPrices, natPrices)
      var judge = algo.mktJudge(c.prices, c.volumes)
      return {
        name: name,
        tier: c.tier,
        priceStr: lp.toLocaleString(),
        ycStr: fmt.fc(yc),
        ycCls: fmt.vcClass(yc),
        tempLabel: tp.l,
        tempScore: tp.s,
        tempCls: tp.c,
        rs: rs,
        rsColor: rs >= 60 ? '#2d8c4e' : rs >= 40 ? '#e67e22' : '#c0392b',
        verdict: judge.verdict,
        verdictCls: judge.cls
      }
    }).filter(function(d) { return d !== null })

    this.setData({ favDetails: details })
  },

  _calcCacheSize: function() {
    try {
      var res = wx.getStorageInfoSync()
      this.setData({ cacheSize: (res.currentSize / 1024).toFixed(1) + 'MB' })
    } catch (e) {
      this.setData({ cacheSize: '未知' })
    }
  },

  addFav: function() {
    var fav = this.data.favCities
    if (fav.length >= MAX_FAV) {
      wx.showToast({ title: '最多关注' + MAX_FAV + '个城市', icon: 'none' })
      return
    }
    var allNames = this.data.allCityNames
    var existing = {}
    fav.forEach(function(n) { existing[n] = true })
    var available = allNames.filter(function(n) { return !existing[n] })

    var self = this
    wx.showActionSheet({
      itemList: available.slice(0, 20),
      success: function(res) {
        var selected = available[res.tapIndex]
        if (selected) {
          fav.push(selected)
          self._saveFav(fav)
          self._buildFavDetails()
        }
      }
    })
  },

  removeFav: function(e) {
    var name = e.currentTarget.dataset.name
    var self = this
    wx.showModal({
      title: '取消关注',
      content: '确定取消关注「' + name + '」？',
      success: function(res) {
        if (res.confirm) {
          var fav = self.data.favCities.filter(function(n) { return n !== name })
          self._saveFav(fav)
          self._buildFavDetails()
        }
      }
    })
  },

  onFavCityTap: function(e) {
    var name = e.currentTarget.dataset.name
    wx.navigateTo({ url: '/pages/city/index?name=' + encodeURIComponent(name) })
  },

  toggleMethod: function() {
    this.setData({ showMethod: !this.data.showMethod })
  },

  clearCache: function() {
    var self = this
    wx.showModal({
      title: '清除缓存',
      content: '将清除所有城市数据缓存，下次打开时重新加载',
      success: function(res) {
        if (res.confirm) {
          dataService.clearCache()
          self._calcCacheSize()
          wx.showToast({ title: '缓存已清除', icon: 'success' })
        }
      }
    })
  },

  onShareAppMessage: function() {
    return {
      title: '房产趋势看板 — 数据驱动购房决策',
      path: '/pages/index/index'
    }
  }
})
