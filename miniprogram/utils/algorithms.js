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
  if (n >= 4) {
    var c1 = (p[n - 3] - p[n - 4]) / p[n - 4] * 100
    var c2 = (p[n - 2] - p[n - 3]) / p[n - 3] * 100
    var c3 = (p[n - 1] - p[n - 2]) / p[n - 2] * 100
    if (c3 > c2 && c2 > c1) { s.sd = 1; d.sd = '跌幅连续收窄: ' + c1.toFixed(2) + '%→' + c2.toFixed(2) + '%→' + c3.toFixed(2) + '%' }
    else if (c3 > c2) { d.sd = '部分收窄: ' + c2.toFixed(2) + '%→' + c3.toFixed(2) + '%' }
    else { d.sd = '未收窄: ' + c2.toFixed(2) + '%→' + c3.toFixed(2) + '%' }
  }
  if (n >= 2) {
    var lc = Math.abs((p[n - 1] - p[n - 2]) / p[n - 2] * 100)
    var av = v.slice(-7, -1).reduce(function(a, b) { return a + b }, 0) / Math.max(1, v.slice(-7, -1).length)
    var lv = v[n - 1]
    if (s.sd && lc <= 0.3 && lv >= av * 0.8) {
      s.st = 1; d.st = '波动仅' + lc.toFixed(2) + '%, 量维持' + (lv / av * 100).toFixed(0) + '%'
    } else {
      d.st = '波动' + lc.toFixed(2) + '%' + (lc > 0.3 ? '(>0.3%)' : '') + ', 量' + (lv / (av || 1) * 100).toFixed(0) + '%' + (!s.sd ? ' [需先止跌]' : '')
    }
  }
  if (n >= 3) {
    var cl = (p[n - 1] - p[n - 2]) / p[n - 2] * 100
    var cp2 = (p[n - 2] - p[n - 3]) / p[n - 3] * 100
    var av2 = v.slice(-7, -1).reduce(function(a, b) { return a + b }, 0) / Math.max(1, v.slice(-7, -1).length)
    var ma = p.slice(-5).reduce(function(a, b) { return a + b }, 0) / 5
    if (s.st && cl > 0 && cp2 > 0 && v[n - 1] > av2 && p[n - 1] > ma) {
      s.rc = 1; d.rc = '连涨2月 ' + cp2.toFixed(2) + '%/' + cl.toFixed(2) + '%, 量价齐升'
    } else {
      var r = []
      if (!s.st) r.push('需先走平')
      if (cl <= 0 || cp2 <= 0) r.push('未连续正涨')
      if (v[n - 1] <= av2) r.push('量不足')
      if (p[n - 1] <= ma) r.push('价<MA5')
      d.rc = r.join('·')
    }
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
  var sg = dSg(p, v).s
  var dx = vpDx(p, v)
  var streak = 0, dir = p[n - 1] >= p[n - 2] ? 1 : -1
  for (var i = n - 1; i > 0; i--) {
    if ((p[i] >= p[i - 1] ? 1 : -1) === dir) streak++
    else break
  }
  if (sg.rc) return { verdict: '趋势性回暖', conf: 5, cls: 'tp', detail: '量价齐升已确认，连续正涨' + streak + '月', hint: '可积极看房' }
  if (sg.st && mo > 0.05) return { verdict: '止稳向好', conf: 4, cls: 'tp', detail: '价格走平+动量转正(' + mo.toFixed(2) + '%)，有转折迹象', hint: '可开始关注' }
  if (sg.st) return { verdict: '底部盘整', conf: 3, cls: 'tn', detail: '波动极小，等待方向突破', hint: '继续观察1-2月' }
  if (sg.sd && m1 > 0) return { verdict: '止跌反弹', conf: 3, cls: 'tn', detail: '跌幅收窄+最新月转正，需连续确认', hint: '关注下月能否持续' }
  if (sg.sd) return { verdict: '止跌企稳', conf: 2, cls: 'tn', detail: '跌幅在收窄，尚未转正', hint: '底部信号初现，继续观望' }
  if (m3 > 0 && m6 < -1) return { verdict: '技术性反弹', conf: 2, cls: 'tn', detail: '短期转正但中期仍跌' + m6.toFixed(1) + '%，可能超跌反弹', hint: '不宜追涨，等待确认' }
  if (Math.abs(m3) < 0.5 && Math.abs(m1) < 0.3) return { verdict: '窄幅震荡', conf: 2, cls: 'ti', detail: '近3月波动仅' + m3.toFixed(1) + '%，方向不明', hint: '观望等待信号' }
  if (m3 < 0 && mo > 0) return { verdict: '跌幅收窄', conf: 2, cls: 'tn', detail: '仍在下跌但速度放缓(动量+' + mo.toFixed(2) + '%)', hint: '下行减速，留意拐点' }
  if (m3 < 0 && mo <= 0) return { verdict: '持续下行', conf: 1, cls: 'tng', detail: '近3月' + m3.toFixed(1) + '%，跌势未减', hint: '建议等待止跌信号' }
  if (m3 > 0 && dx.tag === '量价齐升') return { verdict: '健康上行', conf: 4, cls: 'tp', detail: '涨价有成交支撑，上涨可持续', hint: '较好的入场时机' }
  if (m3 > 0 && mo > 0) return { verdict: '温和上行', conf: 3, cls: 'tp', detail: '近3月+' + m3.toFixed(1) + '%，动量仍在加速', hint: '趋势向好但需确认量能' }
  return { verdict: '方向不明', conf: 1, cls: 'ti', detail: '多空交织，暂无明确趋势', hint: '观望' }
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
  getTop1: getTop1
}
