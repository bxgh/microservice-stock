import { apiClient } from './client';
import type { HotStock, Sector, QueryResult } from '../types';

interface AkShareHotStock {
    rank: number;
    code: string;
    name: string;
    price: number;
    change_pct: number;
}

export const marketApi = {
    // PyWencai: Natural Language Query
    queryStocks: async (query: string, perpage: number = 30): Promise<QueryResult> => {
        return apiClient.post<unknown, QueryResult>('/wencai/query', { q: query, perpage });
    },
    // AkShare: Get Hot Rank
    getHotRank: async (limit: number = 20): Promise<HotStock[]> => {
        // raw data from AkShare: [{ code, name, price, change_pct, ... }]
        const rawData = await apiClient.get<unknown, AkShareHotStock[]>('/akshare/rank/hot', { params: { limit } });
        return rawData.map(item => ({
            rank: item.rank,
            code: item.code,
            name: item.name,
            price: item.price,
            change_percent: item.change_pct, // Map change_pct to change_percent
        }));
    },

    // PyWencai: Get Hot Sectors
    getHotSectors: async (limit: number = 10): Promise<Sector[]> => {
        // raw data from PyWencai: [{ "股票简称": "xxx", "最新涨跌幅": "xxx", ... }]
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const rawData = await apiClient.get<unknown, any[]>('/wencai/sector/hot', { params: { limit } });

        // Need to find the correct keys dynamically or fallback
        return rawData.map(item => {
            // Try to find name and change percent from Chinese keys
            const name = item['股票简称'] || item['name'] || item['板块名称'] || 'Unknown';
            const changeStr = item['最新涨跌幅'] || item['change_percent'] || item['涨跌幅'] || '0';
            const change = parseFloat(changeStr);

            return {
                name: name,
                change_percent: isNaN(change) ? 0 : change,
                code: item['股票代码'] || item['code'],
            };
        });
    }
};
