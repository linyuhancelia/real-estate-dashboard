var BASE_URL = 'https://linyuhancelia.github.io/real-estate-dashboard/data'
var CACHE_TTL = 7 * 24 * 60 * 60 * 1000

var _cityFiles = null

function request(url) {
  return new Promise(function(resolve, reject) {
    wx.request({
      url: url,
      method: 'GET',
      dataType: 'json',
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
  return request(BASE_URL + '/summary.json').then(function(data) {
    _cityFiles = data.meta.city_files || {}
    setCache('summary', data)
    return data
  })
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
  return request(BASE_URL + '/city/' + code + '.json').then(function(data) {
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
  BASE_URL: BASE_URL
}
