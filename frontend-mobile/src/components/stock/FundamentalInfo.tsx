import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { stockApi } from '../../api/stock';
import type { StockValuation, StockFinance, StockInfo } from '../../types';

interface FundamentalInfoProps {
    code: string;
}

const FundamentalInfo: React.FC<FundamentalInfoProps> = ({ code }) => {
    const { data: valuation } = useQuery<StockValuation>({
        queryKey: ['valuation', code],
        queryFn: () => stockApi.getValuation(code),
        enabled: !!code,
    });

    const { data: finance } = useQuery<StockFinance>({
        queryKey: ['finance', code],
        queryFn: () => stockApi.getFinance(code),
        enabled: !!code,
    });

    const { data: info } = useQuery<StockInfo>({
        queryKey: ['info', code],
        queryFn: () => stockApi.getIndustry(code),
        enabled: !!code,
    });

    return (
        <div className="bg-white rounded-lg shadow-sm p-4 mt-4">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-800">{info?.name || code}</h2>
                <span className="text-xs bg-blue-100 text-blue-500 px-2 py-1 rounded">{info?.industry || 'Unknown'}</span>
            </div>

            {/* Valuation Grid */}
            <div className="grid grid-cols-3 gap-4 mb-4 border-b border-gray-50 pb-4">
                <div className="text-center">
                    <div className="text-xs text-gray-500">PE (TTM)</div>
                    <div className="font-bold text-gray-900">{valuation?.pe_ttm?.toFixed(2) || '-'}</div>
                </div>
                <div className="text-center">
                    <div className="text-xs text-gray-500">PB</div>
                    <div className="font-bold text-gray-900">{valuation?.pb?.toFixed(2) || '-'}</div>
                </div>
                <div className="text-center">
                    <div className="text-xs text-gray-500">Mkt Cap</div>
                    <div className="font-bold text-gray-900">
                        {valuation?.total_market_value ? (valuation.total_market_value / 100000000).toFixed(0) + '亿' : '-'}
                    </div>
                </div>
            </div>

            {/* Financial Grid */}
            <h3 className="text-sm font-medium text-gray-700 mb-2">Financials (Latest)</h3>
            <div className="space-y-2">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Revenue</span>
                    <span className="font-medium">{finance?.revenue ? (finance.revenue / 100000000).toFixed(2) + '亿' : '-'}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Net Profit</span>
                    <span className="font-medium">{finance?.net_profit ? (finance.net_profit / 100000000).toFixed(2) + '亿' : '-'}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-500">ROE</span>
                    <span className="font-medium">{finance?.roe ? finance.roe.toFixed(2) + '%' : '-'}</span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Gross Margin</span>
                    <span className="font-medium">{finance?.gross_margin ? finance.gross_margin.toFixed(2) + '%' : '-'}</span>
                </div>

                <div className="text-right text-xs text-gray-300 mt-2">
                    Date: {finance?.report_date || '-'}
                </div>
            </div>
        </div>
    );
};

export default FundamentalInfo;
