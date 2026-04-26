# 第 1 章 · 微信小程序前端 (E3)

## E3-S1:看板首屏 wxml

```xml
<!-- pages/dashboard/dashboard.wxml -->
<page-meta>
  <view class="dashboard">

    <!-- ============= 顶部标题栏 ============= -->
    <view class="header">
      <view class="header-title">盘后复盘 · 市场全景</view>
      <view class="header-date">{{trade_date}}</view>
    </view>

    <!-- ============= 模块 1:核心指数 ============= -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">核心指数</view>
        <view class="card-title-en">CORE INDICES</view>
      </view>

      <view class="index-list">
        <view class="index-row" wx:for="{{indices}}" wx:key="code">
          <view class="index-name">{{item.name}}</view>
          <view class="index-close mono">{{item.close}}</view>
          <view class="index-pct mono {{item.pct >= 0 ? 'up' : 'down'}}">
            {{item.pct >= 0 ? '↑' : '↓'}} {{item.pct_display}}
          </view>
        </view>
      </view>
    </view>

    <!-- ============= 模块 2:成交活跃度 ============= -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">全市场成交</view>
        <view class="card-title-en">TURNOVER</view>
      </view>

      <view class="turnover-main">
        <text class="turnover-num mono">{{turnover.total}}</text>
        <text class="turnover-unit">万亿</text>
      </view>

      <view class="turnover-sub">
        <view class="sub-row">
          <text class="sub-label">较 5 日均值</text>
          <text class="sub-value mono {{turnover.vs_ma5_color}}">{{turnover.vs_ma5}}</text>
        </view>
        <view class="sub-row">
          <text class="sub-label">较 20 日均值</text>
          <text class="sub-value mono {{turnover.vs_ma20_color}}">{{turnover.vs_ma20}}</text>
        </view>
        <view class="sub-row">
          <text class="sub-label">1 年分位</text>
          <text class="sub-value mono">{{turnover.pctile}}</text>
        </view>
      </view>
    </view>

    <!-- ============= 模块 3:涨跌家数 ============= -->
    <view class="card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">涨跌家数</view>
        <view class="card-title-en">BREADTH</view>
      </view>

      <view class="breadth-grid">
        <view class="breadth-cell">
          <text class="cell-label">上涨</text>
          <text class="cell-num mono up">{{breadth.up}}</text>
        </view>
        <view class="breadth-cell">
          <text class="cell-label">涨停</text>
          <text class="cell-num mono up">{{breadth.limit_up}}</text>
        </view>
        <view class="breadth-cell">
          <text class="cell-label">下跌</text>
          <text class="cell-num mono down">{{breadth.down}}</text>
        </view>
        <view class="breadth-cell">
          <text class="cell-label">跌停</text>
          <text class="cell-num mono down">{{breadth.limit_down}}</text>
        </view>
        <view class="breadth-cell">
          <text class="cell-label">平盘</text>
          <text class="cell-num mono">{{breadth.flat}}</text>
        </view>
        <view class="breadth-cell">
          <text class="cell-label">炸板</text>
          <text class="cell-num mono neutral">{{breadth.blast}}</text>
        </view>
      </view>

      <view class="breadth-extra">
        <view class="extra-row">
          <text class="extra-label">涨跌比</text>
          <text class="extra-value mono {{breadth.ratio_color}}">{{breadth.ratio}}</text>
        </view>
        <view class="extra-row">
          <text class="extra-label">最高板</text>
          <text class="extra-value mono">{{breadth.max_board}} 板</text>
        </view>
        <view class="extra-row">
          <text class="extra-label">创 60 日新高</text>
          <text class="extra-value mono up">{{breadth.high_60d}}</text>
        </view>
        <view class="extra-row">
          <text class="extra-label">创 60 日新低</text>
          <text class="extra-value mono down">{{breadth.low_60d}}</text>
        </view>
      </view>
    </view>

    <!-- ============= 模块 4:市场状态 ============= -->
    <view class="card regime-card">
      <view class="card-side-bar"></view>
      <view class="card-header">
        <view class="card-title-cn">关键判定</view>
        <view class="card-title-en">REGIME</view>
      </view>

      <view class="regime-main">
        <text class="regime-label">市场状态</text>
        <text class="regime-value">{{regime.label}}</text>
      </view>

      <view class="regime-desc">{{regime.desc}}</view>
    </view>

  </view>
</page-meta>
```

## E3-S2:看板样式 wxss

```css
/* pages/dashboard/dashboard.wxss */

/* ============= 主题变量 ============= */
page {
  --bg:           #0f0e0c;
  --bg-card:     #1a1714;
  --bg-elev:     #232019;
  --ink:         #ede3cc;
  --ink-dim:     #b5a98e;
  --ink-mute:    #776d58;
  --amber:       #d4a23e;
  --amber-bright:#f0c968;
  --up:          #e5644f;
  --down:        #5ca478;
  --flat:        #888888;
  --neutral:     #c99339;
  --hair:        #2a2520;

  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.mono {
  font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
  font-feature-settings: 'tnum';
}

.up    { color: var(--up); }
.down  { color: var(--down); }
.flat  { color: var(--flat); }
.neutral { color: var(--neutral); }

/* ============= 整体布局 ============= */
.dashboard {
  padding: 16rpx;
  min-height: 100vh;
}

/* ============= 顶部标题 ============= */
.header {
  padding: 24rpx 16rpx;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1rpx solid var(--hair);
  margin-bottom: 16rpx;
}
.header-title {
  font-size: 36rpx;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 2rpx;
}
.header-date {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 24rpx;
  color: var(--ink-mute);
}

/* ============= 卡片通用 ============= */
.card {
  position: relative;
  background: var(--bg-card);
  margin-bottom: 16rpx;
  padding: 24rpx 24rpx 24rpx 32rpx;
  border-radius: 4rpx;
}
.card-side-bar {
  position: absolute;
  top: 24rpx; bottom: 24rpx; left: 0;
  width: 4rpx;
  background: var(--amber);
}
.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 24rpx;
  padding-bottom: 16rpx;
  border-bottom: 1rpx solid var(--hair);
}
.card-title-cn {
  font-size: 32rpx;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 2rpx;
}
.card-title-en {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 20rpx;
  color: var(--amber);
  letter-spacing: 4rpx;
}

/* ============= 模块 1:核心指数 ============= */
.index-list { display: flex; flex-direction: column; }
.index-row {
  display: flex;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid var(--hair);
}
.index-row:last-child { border-bottom: none; }
.index-name {
  flex: 0 0 140rpx;
  font-size: 28rpx;
  color: var(--ink-dim);
}
.index-close {
  flex: 1;
  text-align: right;
  font-size: 32rpx;
  color: var(--ink);
}
.index-pct {
  flex: 0 0 160rpx;
  text-align: right;
  font-size: 28rpx;
  font-weight: 600;
}

/* ============= 模块 2:成交 ============= */
.turnover-main {
  display: flex;
  align-items: baseline;
  justify-content: center;
  margin-bottom: 24rpx;
}
.turnover-num {
  font-size: 88rpx;
  font-weight: 600;
  color: var(--amber-bright);
  letter-spacing: 2rpx;
}
.turnover-unit {
  font-size: 28rpx;
  color: var(--ink-dim);
  margin-left: 12rpx;
}
.turnover-sub { display: flex; flex-direction: column; }
.sub-row {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-top: 1rpx solid var(--hair);
}
.sub-label { font-size: 26rpx; color: var(--ink-dim); }
.sub-value { font-size: 28rpx; color: var(--ink); }

/* ============= 模块 3:涨跌家数 ============= */
.breadth-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rpx;
  background: var(--hair);
  margin-bottom: 16rpx;
}
.breadth-cell {
  background: var(--bg-card);
  padding: 24rpx 12rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.cell-label {
  font-size: 24rpx;
  color: var(--ink-mute);
  margin-bottom: 12rpx;
}
.cell-num {
  font-size: 44rpx;
  font-weight: 600;
}
.breadth-extra { padding-top: 12rpx; }
.extra-row {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-top: 1rpx solid var(--hair);
}
.extra-label { font-size: 26rpx; color: var(--ink-dim); }
.extra-value { font-size: 28rpx; color: var(--ink); }

/* ============= 模块 4:市场状态 ============= */
.regime-card .card-side-bar { background: var(--amber-bright); }
.regime-main {
  display: flex;
  align-items: baseline;
  margin-bottom: 16rpx;
}
.regime-label {
  font-size: 26rpx;
  color: var(--ink-dim);
  margin-right: 16rpx;
}
.regime-value {
  font-size: 40rpx;
  font-weight: 600;
  color: var(--amber-bright);
  letter-spacing: 2rpx;
}
.regime-desc {
  font-size: 26rpx;
  color: var(--ink-dim);
  line-height: 1.6;
  padding: 16rpx;
  background: var(--bg-elev);
  border-left: 4rpx solid var(--amber);
}
```

## E3-S3:看板逻辑 js(数据结构示例)

```javascript
// pages/dashboard/dashboard.js
Page({
  data: {
    trade_date: '2026-04-25',
    indices: [
      { code: '000001.SH', name: '上证综指',  close: '3,234.56', pct: 0.0085, pct_display: '0.85%' },
      { code: '399001.SZ', name: '深证成指',  close: '10,234.5', pct: -0.0032, pct_display: '0.32%' },
      // ... 共 10 行
    ],
    turnover: {
      total: '1.18',           // 万亿
      vs_ma5: '+12.3%',
      vs_ma5_color: 'up',
      vs_ma20: '+8.7%',
      vs_ma20_color: 'up',
      pctile: '82.4%'
    },
    breadth: {
      up: 3124, down: 1876, flat: 234,
      limit_up: 45, limit_down: 12, blast: 8,
      ratio: '1.66', ratio_color: 'up',
      max_board: 5,
      high_60d: 89, low_60d: 23
    },
    regime: {
      label: '结构性分化',
      desc: '涨跌家数偏强,但成交集中度高,建议关注主线持续性'
    }
  },

  onLoad() {
    this.fetchDashboardData();
  },

  async fetchDashboardData() {
    // 调用后端接口:GET /api/dashboard/l1?date=2026-04-25
    // 后端 SQL:SELECT * FROM ads_l1_market_overview WHERE trade_date = ?
    // 数据加工层负责:
    //   - 涨跌幅小数转百分比字符串
    //   - 成交额元转万亿(/ 1e12)
    //   - market_regime 枚举转中文标签
  }
});
```
