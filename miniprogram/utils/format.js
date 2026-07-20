var CC = ['#e74c3c', '#c0392b', '#8e44ad', '#2980b9', '#e67e22', '#1abc9c', '#34495e', '#9b59b6', '#d4a017', '#16a085', '#27ae60', '#00bcd4', '#607d8b', '#ff5722', '#4caf50', '#795548', '#ff9800', '#009688', '#673ab7', '#03a9f4']

var _ci = 0

function resetColorIndex() { _ci = 0 }

function getColor(name) {
  if (name === '上海') return '#e74c3c'
  if (name === '香港') return '#d4a017'
  return CC[(_ci++) % CC.length]
}

function fc(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
}

function fc2(v) {
  return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'
}

function vcClass(v) {
  return v >= 0.05 ? 'vu' : v <= -0.05 ? 'vd' : 'vn'
}

function tagClass(cls) {
  return 'tag tag-' + cls
}

function tempClass(c) {
  return 'tag tag-' + c
}

function priceStr(p) {
  if (p >= 10000) return (p / 10000).toFixed(1) + '万'
  return p.toLocaleString()
}

function monthsShort(months) {
  return months.map(function(m) {
    return m.length > 5 ? m.slice(2) : m
  })
}

function baselineChange(prices) {
  if (!prices || prices.length < 2) return []
  var b = prices[0]
  return prices.map(function(p) {
    return +((p - b) / b * 100).toFixed(2)
  })
}

module.exports = {
  CC: CC,
  resetColorIndex: resetColorIndex,
  getColor: getColor,
  fc: fc,
  fc2: fc2,
  vcClass: vcClass,
  tagClass: tagClass,
  tempClass: tempClass,
  priceStr: priceStr,
  monthsShort: monthsShort,
  baselineChange: baselineChange
}
