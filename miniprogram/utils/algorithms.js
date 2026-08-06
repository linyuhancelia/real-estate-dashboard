/**
 * algorithms.js — 房产趋势分析核心算法
 * 从 web 版 index.html 直接搬运，纯计算逻辑，无 DOM 依赖
 */

function cC(p, n) {
  var l = p.length, i = l - 1 - n
  return i < 0 ? 0 : ((p[l - 1] - p[i]) / p[i]) * 100
}

function cSl(p, s, e) {
  return (e <= s || s < 0) ? 0 : (p[e] - p[s]) / p[s] * 100 / (e - s)
}

function cMo(p) {
  var n = p.length
  return n < 7 ? 0 : cSl(p, n - 4, n - 1) - cSl(p, n - 7, n - 4)
}

function cTp(p, v) {
  var n = p.length
  var pm = Math.max(0, Math.min(100, 50 + cC(p, 3) * 15))
  var rv = v.slice(-3).reduce(function(a, b) { return a + b }, 0) / 3
  var ps = v.slice(-9, -3)
  var pv = ps.length ? ps.reduce(function(a, b) { return a + b }, 0) / ps.length : rv
  var vm = Math.max(0, Math.min(100, (pv > 0 ? rv / pv : 1) * 50))
  var c = 0
  var ld = p[n - 1] >= p[n - 2] ? 1 : -1
  for (var i = n - 1; i > 0; i--) {
    if ((p[i] >= p[i - 1] ? 1 : -1) === ld) c++
    else break
  }
  var pe = Math.max(0, Math.min(100, c * 12 + (ld > 0 ? 20 : 0)))
  var s = pm * 0.4 + vm * 0.3 + pe * 0.3
  if (s > 65) return { s: Math.round(s), l: '热', c: 'th' }
  if (s > 35) return { s: Math.round(s), l: '平', c: 'tw' }
  return { s: Math.round(s), l: '寒', c: 'tc' }
}

function isReliable(prices, window) {
  var w = window || 13
  if (!prices || prices.length < w) return false
  var seg = prices.slice(-w)
  var same = 0
  for (var i = 1; i < seg.length; i++) {
    if (seg[i] === seg[i - 1]) same++
    var chg = Math.abs((seg[i] - seg[i - 1]) / seg[i - 1])
    if (chg > 0.10) return false
  }
  return same < Math.floor(w / 2)
}

function detectJumps(prices, meta) {
  if (!prices || prices.length < 3) return []
  var months = (meta && meta.months) || []
  var jumps = []
  for (var i = 1; i < prices.length; i++) {
    var chg = (prices[i] - prices[i - 1]) / prices[i - 1]
    if (Math.abs(chg) > 0.08) {
      var label = months[i] || ('第' + (i + 1) + '月')
      jumps.push({
        idx: i,
        month: label,
        from: prices[i - 1],
        to: prices[i],
        pct: (chg * 100).toFixed(1)
      })
    }
  }
  return jumps
}

function cRS(p, all, natPrices) {
  var pds = [{ m: 1, w: 0.4 }, { m: 3, w: 0.35 }, { m: 12, w: 0.25 }]
  var wp = 0
  pds.forEach(function(pd) {
    var mc = cC(p, Math.min(pd.m, p.length - 1))
    var nc = cC(natPrices, Math.min(pd.m, natPrices.length - 1))
    var ex = mc - nc
    var ae = all.map(function(q) {
      return cC(q, Math.min(pd.m, q.length - 1)) - nc
    }).sort(function(a, b) { return a - b })
    wp += (ae.filter(function(e) { return e <= ex }).length / ae.length) * 100 * pd.w
  })
  return Math.round(wp)
}

function dSg(p, v) {
  var n = p.length, s = { sd: 0, st: 0, rc: 0 }, d = { sd: '', st: '', rc: '' }
  if (n < 4) return { s: s, d: d }

  var m1 = (p[n - 1] - p[n - 2]) / p[n - 2] * 100
  var m3 = (p[n - 1] - p[n - 4]) / p[n - 4] * 100
  var mo = n >= 7 ? cSl(p, n - 4, n - 1) - cSl(p, n - 7, n - 4) : 0
  var av = v.slice(-7, -1).reduce(function(a, b) { return a + b }, 0) / Math.max(1, v.slice(-7, -1).length)
  var lv = v[n - 1]
  var ma = p.slice(-5).reduce(function(a, b) { return a + b }, 0) / 5

  if (m3 > 0.3 && m1 > 0 && p[n - 1] > ma) {
    s.rc = 1; s.st = 1; s.sd = 1
    d.rc = '3月+' + m3.toFixed(2) + '%, 最新月+' + m1.toFixed(2) + '%'
    d.st = '已进入回升阶段'
    d.sd = '已进入回升阶段'
  } else if (Math.abs(m3) < 0.6 && Math.abs(m1) <= 0.4 && lv >= av * 0.7) {
    s.st = 1; s.sd = 1
    d.st = '波动' + Math.abs(m1).toFixed(2) + '%, 3月' + m3.toFixed(2) + '%'
    d.sd = '已走平'
    var r = []
    if (m3 <= 0.3) r.push('3月涨幅不足(' + m3.toFixed(2) + '%)')
    if (m1 <= 0) r.push('最新月未正涨')
    if (p[n - 1] <= ma) r.push('价<MA5')
    d.rc = r.length ? r.join('·') : '接近回升'
  } else if (mo > 0 || m1 >= 0) {
    s.sd = 1
    d.sd = mo > 0 ? '动量转正(+' + mo.toFixed(2) + '%)' : '最新月' + m1.toFixed(2) + '%'
    d.st = Math.abs(m3) >= 1.0 ? '3月跌幅' + m3.toFixed(2) + '%(未企稳)' : '量不足(' + (lv / av * 100).toFixed(0) + '%)'
    d.rc = '需先走平'
  } else {
    d.sd = '仍下跌(月' + m1.toFixed(2) + '%, 动量' + mo.toFixed(2) + '%)'
    d.st = '需先止跌'
    d.rc = '需先走平'
  }
  return { s: s, d: d }
}

function vpDx(ps, vs) {
  var n = ps.length
  if (n < 4) return { tag: '数据不足', cls: 'ti', tip: '' }
  var rp = ps.slice(-3), pp = ps.slice(-6, -3), rv = vs.slice(-3), pv = vs.slice(-6, -3)
  var rpA = rp.reduce(function(a, b) { return a + b }, 0) / 3
  var ppA = pp.reduce(function(a, b) { return a + b }, 0) / Math.max(1, pp.length)
  var rvA = rv.reduce(function(a, b) { return a + b }, 0) / 3
  var pvA = pv.reduce(function(a, b) { return a + b }, 0) / Math.max(1, pv.length)
  var pUp = rpA > ppA * 1.002, pDn = rpA < ppA * 0.998
  var vUp = rvA > pvA * 1.05, vDn = rvA < pvA * 0.95
  if (pUp && vUp) return { tag: '量价齐升', cls: 'tp', tip: '最健康信号：涨价有成交支撑，上涨可持续' }
  if (pDn && vUp) return { tag: '放量下跌', cls: 'tng', tip: '抛压释放/恐慌出逃，尚未见底，谨慎观望' }
  if (pUp && vDn) return { tag: '缩量上涨', cls: 'tn', tip: '量价背离：涨价缺乏买盘支撑，可能虚涨' }
  if (pDn && vDn) return { tag: '缩量阴跌', cls: 'tng', tip: '有价无市，观望情绪浓，好消息是抛压也在减小' }
  if (!pUp && !pDn && vUp) return { tag: '放量横盘', cls: 'tn', tip: '买卖博弈激烈，可能是变盘前兆' }
  if (!pUp && !pDn && vDn) return { tag: '缩量横盘', cls: 'ti', tip: '市场冷淡，买卖双方都在等待信号' }
  return { tag: '量价平稳', cls: 'ti', tip: '市场相对均衡，暂无明显方向' }
}

function mktJudge(p, v) {
  var n = p.length
  if (n < 6) return { verdict: '数据不足', conf: 0, cls: 'ti', detail: '', hint: '' }

  var m1 = cC(p, 1), m3 = cC(p, 3), m6 = cC(p, Math.min(6, n - 1))
  var mo = cMo(p)
  var dx = vpDx(p, v)

  var streak = 0, dir = p[n - 1] >= p[n - 2] ? 1 : -1
  for (var i = n - 1; i > 0; i--) {
    if ((p[i] >= p[i - 1] ? 1 : -1) === dir) streak++
    else break
  }

  var rv = v.slice(-3).reduce(function(a, b) { return a + b }, 0) / 3
  var pv = v.slice(-9, -3)
  var pvA = pv.length ? pv.reduce(function(a, b) { return a + b }, 0) / pv.length : rv
  var vRatio = pvA > 0 ? rv / pvA : 1

  // === 上行市场 (m3 > 0.5%) ===
  if (m3 > 0.5) {
    if (streak >= 4 && mo > 0.05 && vRatio > 1.05) {
      return { verdict: '趋势性回暖', conf: 5, cls: 'tp',
        detail: '连涨' + streak + '月，量价齐升，动量加速中',
        hint: '上行趋势确立，可积极看房' }
    }
    if (streak >= 4 && vRatio >= 0.85) {
      return { verdict: '稳步上行', conf: 4, cls: 'tp',
        detail: '连涨' + streak + '月(+' + m3.toFixed(1) + '%)，成交平稳',
        hint: '上行通道中，趋势延续' }
    }
    if (m3 > 0.5 && m6 < -2) {
      return { verdict: '超跌反弹', conf: 2, cls: 'tn',
        detail: '短期+' + m3.toFixed(1) + '%，但半年仍跌' + m6.toFixed(1) + '%',
        hint: '反弹持续性待验证，不宜追涨' }
    }
    if (vRatio < 0.8 && streak >= 2) {
      return { verdict: '缩量上涨', conf: 2, cls: 'tn',
        detail: '价涨+' + m3.toFixed(1) + '%但量缩' + ((1 - vRatio) * 100).toFixed(0) + '%',
        hint: '上涨缺乏买盘支撑，警惕回调' }
    }
    if (mo > 0) {
      return { verdict: '温和回升', conf: 3, cls: 'tp',
        detail: '近3月+' + m3.toFixed(1) + '%，动量+' + mo.toFixed(2) + '%加速中',
        hint: '趋势向好，可关注' }
    }
    return { verdict: '上行放缓', conf: 3, cls: 'tn',
      detail: '仍涨+' + m3.toFixed(1) + '%但涨幅收窄(动量' + mo.toFixed(2) + '%)',
      hint: '趋势未逆转但力度减弱，关注量能' }
  }

  // === 下行市场 (m3 < -0.5%) ===
  if (m3 < -0.5) {
    if (mo < -0.08 && vRatio > 1.1) {
      return { verdict: '加速下行', conf: 1, cls: 'tng',
        detail: '跌幅扩大(动量' + mo.toFixed(2) + '%)且放量抛售',
        hint: '趋势恶化，建议观望' }
    }
    if (mo <= 0) {
      return { verdict: '持续下行', conf: 1, cls: 'tng',
        detail: '近3月' + m3.toFixed(1) + '%，跌势未减',
        hint: '下行通道中，等待止跌信号' }
    }
    if (mo > 0 && m1 > -0.1) {
      return { verdict: '止跌企稳', conf: 2, cls: 'tn',
        detail: '跌幅快速收窄，最新月仅' + m1.toFixed(2) + '%',
        hint: '底部信号初现，关注连续性' }
    }
    return { verdict: '跌幅收窄', conf: 2, cls: 'tn',
      detail: '仍跌' + m3.toFixed(1) + '%但速度放缓(动量+' + mo.toFixed(2) + '%)',
      hint: '下行减速，留意拐点' }
  }

  // === 盘整市场 (|m3| <= 0.5%) ===
  if (m1 > 0.2 && m6 < -1.5) {
    return { verdict: '止跌反弹', conf: 2, cls: 'tn',
      detail: '最新月转正+' + m1.toFixed(2) + '%，半年仍跌' + m6.toFixed(1) + '%',
      hint: '需连续确认，单月不构成趋势' }
  }
  if (m6 < -1) {
    if (mo > 0.05) {
      return { verdict: '止稳向好', conf: 3, cls: 'tn',
        detail: '跌后企稳，动量已转正(+' + mo.toFixed(2) + '%)',
        hint: '有转折迹象，可开始关注' }
    }
    return { verdict: '底部盘整', conf: 2, cls: 'tn',
      detail: '跌势已止，近3月波动' + m3.toFixed(2) + '%',
      hint: '底部构筑中，等待方向突破' }
  }
  if (m6 > 1) {
    return { verdict: '高位整理', conf: 3, cls: 'tn',
      detail: '涨后进入整理，半年+' + m6.toFixed(1) + '%',
      hint: '消化涨幅中，关注方向选择' }
  }
  return { verdict: '窄幅震荡', conf: 2, cls: 'ti',
    detail: '近3月波动' + m3.toFixed(2) + '%，方向不明',
    hint: '观望等待信号' }
}

var NBS_CITIES = ['北京','上海','广州','深圳','天津','石家庄','太原','呼和浩特','沈阳','大连','长春','哈尔滨','南京','杭州','宁波','合肥','福州','厦门','南昌','济南','青岛','郑州','武汉','长沙','南宁','海口','重庆','成都','贵阳','昆明','西安','兰州','西宁','银川','乌鲁木齐','唐山','秦皇岛','包头','丹东','锦州','吉林','牡丹江','无锡','徐州','扬州','温州','金华','蚌埠','安庆','泉州','九江','赣州','烟台','济宁','洛阳','平顶山','宜昌','襄阳','岳阳','常德','韶关','湛江','惠州','桂林','北海','三亚','泸州','南充','遵义','大理']

function isNbsCity(name) {
  return NBS_CITIES.indexOf(name) >= 0
}

function getTopRiser(cities) {
  var entries = Object.keys(cities)
    .filter(function(n) {
      if (n === '上海') return false
      if (!isNbsCity(n)) return false
      var c = cities[n]
      if (!isReliable(c.prices)) return false
      var m3 = cC(c.prices, 3)
      return m3 > 0
    })
    .map(function(n) {
      var c = cities[n]
      return { name: n, prices: c.prices, m3: cC(c.prices, 3), tier: c.tier }
    })
    .sort(function(a, b) { return b.m3 - a.m3 })
  return entries[0] || null
}

function getTop1(cities, natPrices, allPrices) {
  var hasData = function(p) {
    var t = p.slice(-7)
    return new Set(t).size > 1
  }
  var entries = Object.keys(cities)
    .filter(function(n) { return n !== '上海' && hasData(cities[n].prices) })
    .map(function(n) {
      var d = cities[n]
      return { n: n, mc: Math.abs(cMo(d.prices)), raw: cMo(d.prices), prices: d.prices, volumes: d.volumes }
    })
    .sort(function(a, b) { return b.mc - a.mc })
  return entries[0] || { n: '—', mc: 0, raw: 0, prices: [], volumes: [] }
}

module.exports = {
  cC: cC,
  cSl: cSl,
  cMo: cMo,
  cTp: cTp,
  cRS: cRS,
  dSg: dSg,
  vpDx: vpDx,
  mktJudge: mktJudge,
  getTop1: getTop1,
  getTopRiser: getTopRiser,
  isNbsCity: isNbsCity,
  isReliable: isReliable,
  detectJumps: detectJumps
}
