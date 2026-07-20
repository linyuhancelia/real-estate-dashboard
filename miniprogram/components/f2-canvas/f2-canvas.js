Component({
  properties: {
    canvasId: { type: String, value: 'f2Canvas' },
    width: { type: String, value: '100%' },
    height: { type: String, value: '200px' }
  },

  data: {
    _canvas: null,
    _chart: null
  },

  lifetimes: {
    ready: function() {
      var self = this
      var query = this.createSelectorQuery()
      query.select('#' + this.data.canvasId)
        .fields({ node: true, size: true })
        .exec(function(res) {
          if (!res || !res[0]) return
          var canvas = res[0].node
          var width = res[0].width
          var height = res[0].height
          var dpr = wx.getWindowInfo().pixelRatio
          canvas.width = width * dpr
          canvas.height = height * dpr
          var ctx = canvas.getContext('2d')
          ctx.scale(dpr, dpr)

          self.setData({ _canvas: canvas })
          self.triggerEvent('bindinit', {
            canvas: canvas,
            width: width,
            height: height,
            ctx: ctx,
            pixelRatio: dpr
          })
        })
    },

    detached: function() {
      if (this.data._chart) {
        this.data._chart.destroy()
      }
    }
  },

  methods: {
    setChart: function(chart) {
      this.setData({ _chart: chart })
    },

    touchStart: function(e) {
      if (this.data._chart) {
        this.data._chart.get('bindTouchStart') && this.data._chart.get('bindTouchStart')(e)
      }
    },

    touchMove: function(e) {
      if (this.data._chart) {
        this.data._chart.get('bindTouchMove') && this.data._chart.get('bindTouchMove')(e)
      }
    },

    touchEnd: function(e) {
      if (this.data._chart) {
        this.data._chart.get('bindTouchEnd') && this.data._chart.get('bindTouchEnd')(e)
      }
    }
  }
})
