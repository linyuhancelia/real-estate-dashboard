const dataService = require('./utils/data')

App({
  globalData: {
    summary: null,
    national: null,
    cities: {},
    allPrices: [],
    meta: null,
    loaded: false
  },

  onLaunch() {
    this.loadSummary()
  },

  async loadSummary() {
    try {
      const res = await dataService.loadSummary()
      this.globalData.meta = res.meta
      this.globalData.national = res.national
      this.globalData.cities = res.cities
      this.globalData.allPrices = Object.values(res.cities).map(c => c.prices)
      this.globalData.loaded = true
      if (this._onDataReady) this._onDataReady()
    } catch (e) {
      console.error('[App] loadSummary failed:', e)
    }
  },

  onDataReady(cb) {
    if (this.globalData.loaded) {
      cb()
    } else {
      this._onDataReady = cb
    }
  }
})
