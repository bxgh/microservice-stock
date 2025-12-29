export interface HotStock {
    rank: number;
    code: string;
    name: string;
    price: number;
    change_percent: number; // 涨跌幅
    reason?: string; // 上榜理由 (if available)
}

export interface Sector {
    name: string;
    change_percent: number;
    code?: string; // 板块代码
    market_value?: number; // 流通市值
}

export interface QueryResult {
    data: (string | number)[][];
    columns: string[];
}

export interface KLineData {
    date: string;
    open: string;
    high: string;
    low: string;
    close: string;
    volume: string;
    amount: string;
    adjustflag: string;
}

export interface StockValuation {
    code: string;
    pe: number;
    pe_ttm: number;
    pb: number;
    total_market_value: number;
    circulating_market_value: number;
}

export interface StockFinance {
    code: string;
    revenue: number; // 营收
    net_profit: number; // 净利润
    gross_margin: number; // 毛利率
    net_profit_margin: number; // 净利率
    roe: number;
    revenue_growth_yoy: number; // 营收同比
    report_date: string;
}

export interface StockInfo {
    code: string;
    name: string;
    industry: string;
    listing_date?: string;
}

export interface SchedulerJob {
    id: string;
    name: string;
    next_run_time: string | null;
    trigger: string;
    func?: string;
}

