var BUNDLED = require('../data/bundled_summary')
var CDN_URLS = [
  'https://cdn.jsdelivr.net/gh/linyuhancelia/real-estate-dashboard@main/data',
  'https://raw.githubusercontent.com/linyuhancelia/real-estate-dashboard/main/data'
]
var CACHE_TTL = 7 * 24 * 60 * 60 * 1000

var _cityFiles = null

function request(url) {
  return new Promise(function(resolve, reject) {
    wx.request({
      url: url,
      method: 'GET',
      dataType: 'json',
      timeout: 8000,
      success: function(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(new Error('HTTP ' + res.statusCode))
        }
      },
      fail: function(err) {
        reject(err)
      }
    })
  })
}

function requestWithFallback(path) {
  var i = 0
  function tryNext() {
    if (i >= CDN_URLS.length) return Promise.reject(new Error('all CDNs failed'))
    var url = CDN_URLS[i++] + path
    return request(url).catch(function() { return tryNext() })
  }
  return tryNext()
}

function getCached(key) {
  try {
    var cached = wx.getStorageSync(key)
    if (cached && cached.ts && (Date.now() - cached.ts < CACHE_TTL)) {
      return cached.data
    }
  } catch (e) {}
  return null
}

function setCache(key, data) {
  try {
    wx.setStorageSync(key, { data: data, ts: Date.now() })
  } catch (e) {
    console.warn('[data] cache write failed:', e)
  }
}

function loadSummary() {
  var cached = getCached('summary')
  if (cached) {
    _cityFiles = cached.meta.city_files || {}
    return Promise.resolve(cached)
  }

  _cityFiles = BUNDLED.meta.city_files || {}

  requestWithFallback('/summary.json').then(function(data) {
    _cityFiles = data.meta.city_files || {}
    setCache('summary', data)
  }).catch(function() {})

  return Promise.resolve(BUNDLED)
}

function getCityCode(name) {
  if (_cityFiles && _cityFiles[name]) return _cityFiles[name]
  return name
}

function loadCityDetail(name) {
  var cacheKey = 'city_' + name
  var cached = getCached(cacheKey)
  if (cached) return Promise.resolve(cached)

  var code = getCityCode(name)
  return requestWithFallback('/city/' + code + '.json').then(function(data) {
    setCache(cacheKey, data)
    return data
  })
}

function clearCache() {
  try {
    var keys = wx.getStorageInfoSync().keys
    keys.forEach(function(k) {
      if (k === 'summary' || k.indexOf('city_') === 0) {
        wx.removeStorageSync(k)
      }
    })
  } catch (e) {}
}

module.exports = {
  loadSummary: loadSummary,
  loadCityDetail: loadCityDetail,
  getCityCode: getCityCode,
  clearCache: clearCache,
  BASE_URL: CDN_URLS[0]
}
