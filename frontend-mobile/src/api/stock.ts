import { apiClient } from './client';
import type { KLineData, StockValuation, StockFinance, StockInfo } from '../types';

export const stockApi = {
    // BaoStock: Get K-Line Data
    getKline: async (code: string, startDate?: string, endDate?: string, frequency: string = 'd', adjust: string = '2'): Promise<KLineData[]> => {
        // Correct Path: /baostock/history/kline/{code}
        return apiClient.get<unknown, KLineData[]>(`/baostock/history/kline/${code}`, {
            params: { start_date: startDate, end_date: endDate, frequency, adjust }
        });
    },

    // AkShare: Get Valuation
    getValuation: async (code: string): Promise<StockValuation> => {
        return apiClient.get<unknown, StockValuation>(`/akshare/valuation/${code}`);
    },

    // AkShare: Get Financial Indicators
    getFinance: async (code: string): Promise<StockFinance> => {
        // Note: Endpoint returns expanded indicators
        return apiClient.get<unknown, StockFinance>(`/akshare/finance/indicators/${code}`);
    },

    // AkShare: Get Industry Info
    getIndustry: async (code: string): Promise<StockInfo> => {
        return apiClient.get<unknown, StockInfo>(`/akshare/industry/stock/${code}`);
    }
};
