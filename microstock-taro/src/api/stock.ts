import client from './client';
import type { KLineData, StockValuation, StockFinance, StockInfo } from '../types';

export const stockApi = {
    // BaoStock: Get K-Line Data
    getKline: async (code: string, startDate?: string, endDate?: string, frequency: string = 'd', adjust: string = '2'): Promise<KLineData[]> => {
        // Correct Path: /baostock/history/kline/{code}
        return client.get<KLineData[]>(`/baostock/history/kline/${code}`, {
            start_date: startDate, end_date: endDate, frequency, adjust
        });
    },

    // AkShare: Get Valuation
    getValuation: async (code: string): Promise<StockValuation> => {
        return client.get<StockValuation>(`/akshare/valuation/${code}`);
    },

    // AkShare: Get Financial Indicators
    getFinance: async (code: string): Promise<StockFinance> => {
        // Note: Endpoint returns expanded indicators
        return client.get<StockFinance>(`/akshare/finance/indicators/${code}`);
    },

    // AkShare: Get Industry Info
    getIndustry: async (code: string): Promise<StockInfo> => {
        return client.get<StockInfo>(`/akshare/industry/stock/${code}`);
    }
};
