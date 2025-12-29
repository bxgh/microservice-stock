export default {
    pages: [
        'pages/index/index',
        'pages/market/index',
        'pages/favor/index',
        'pages/news/index',
        'pages/trade/index',
        'pages/detail/index'
    ],
    window: {
        backgroundTextStyle: 'light',
        navigationBarBackgroundColor: '#fff',
        navigationBarTitleText: 'MicroStock',
        navigationBarTextStyle: 'black'
    },
    tabBar: {
        color: "#999999",
        selectedColor: "#333333",
        backgroundColor: "#ffffff",
        borderStyle: "black",
        list: [
            {
                pagePath: "pages/index/index",
                text: "首页",
                iconPath: "assets/icons/home.png",
                selectedIconPath: "assets/icons/home_active.png"
            },
            {
                pagePath: "pages/market/index",
                text: "行情",
                iconPath: "assets/icons/market.png",
                selectedIconPath: "assets/icons/market_active.png"
            },
            {
                pagePath: "pages/favor/index",
                text: "自选",
                iconPath: "assets/icons/star.png",
                selectedIconPath: "assets/icons/star_active.png"
            },
            {
                pagePath: "pages/news/index",
                text: "资讯",
                iconPath: "assets/icons/news.png",
                selectedIconPath: "assets/icons/news_active.png"
            },
            {
                pagePath: "pages/trade/index",
                text: "交易",
                iconPath: "assets/icons/trade.png",
                selectedIconPath: "assets/icons/trade_active.png"
            }
        ]
    }
}

