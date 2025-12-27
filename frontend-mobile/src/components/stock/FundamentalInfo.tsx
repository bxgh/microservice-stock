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

            <div className="flex flex-col gap-8">
                {/* Valuation Grid */}
                <section className="flex flex-col gap-4">
                    <h2 className="text-sm font-bold text-secondary uppercase tracking-widest px-1">Valuation Matrix</h2>
                    <div className="grid grid-cols-2 gap-3">
                        <div className="glass-card flex flex-col gap-1">
                            <span className="text-[10px] text-secondary font-medium">PE Ratio</span>
                            <span className="text-lg font-bold tabular-nums">{valuation?.pe?.toFixed(2) || '--'}</span>
                            <div className="mt-1 h-1 w-full bg-border rounded-full overflow-hidden">
                                <div className="h-full bg-primary" style={{ width: '65%' }} />
                            </div>
                        </div>
                        <div className="glass-card flex flex-col gap-1">
                            <span className="text-[10px] text-secondary font-medium">PB Ratio</span>
                            <span className="text-lg font-bold tabular-nums">{valuation?.pb?.toFixed(2) || '--'}</span>
                            <div className="mt-1 h-1 w-full bg-border rounded-full overflow-hidden">
                                <div className="h-full bg-secondary" style={{ width: '45%' }} />
                            </div>
                        </div>
                    </div>
                </section>

                {/* Financial Health */}
                <section className="flex flex-col gap-4">
                    <h2 className="text-sm font-bold text-secondary uppercase tracking-widest px-1">Financial Health</h2>
                    <div className="bg-card border border-border rounded-2xl overflow-hidden divide-y divide-border">
                        <div className="p-5 flex justify-between items-center">
                            <div className="flex flex-col">
                                <span className="text-xs font-bold">Industry</span>
                                <span className="text-[10px] text-secondary mt-0.5">{info?.industry || '--'}</span>
                            </div>
                            <div className="px-3 py-1 bg-primary bg-opacity-10 rounded-full">
                                <span className="text-[10px] text-primary font-bold">BLUE CHIP</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-2">
                            <div className="p-5 border-r border-border flex flex-col gap-1">
                                <span className="text-[10px] text-secondary">ROE</span>
                                <span className="text-sm font-bold">{finance?.roe?.toFixed(2)}%</span>
                            </div>
                            <div className="p-5 flex flex-col gap-1">
                                <span className="text-[10px] text-secondary">Net Margin</span>
                                <span className="text-sm font-bold">{finance?.net_profit_margin?.toFixed(2)}%</span>
                            </div>
                        </div>

                        <div className="p-5 flex flex-col gap-3">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-secondary">Revenue Growth</span>
                                <span className={`text-xs font-bold ${(finance?.revenue_growth_yoy ?? 0) > 0 ? 'price-up' : 'price-down'}`}>
                                    {finance?.revenue_growth_yoy?.toFixed(2) ?? '--'}%
                                </span>
                            </div>
                            <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${(finance?.revenue_growth_yoy ?? 0) > 0 ? 'bg-success' : 'bg-danger'}`}
                                    style={{ width: `${Math.min(Math.abs(finance?.revenue_growth_yoy ?? 0), 100)}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

export default FundamentalInfo;
