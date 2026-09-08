const { WEB_URL } = require("../../config")

Page({
  data: {
    webUrl: WEB_URL,
    isPlaceholder: WEB_URL.includes("example.com"),
  },
})
