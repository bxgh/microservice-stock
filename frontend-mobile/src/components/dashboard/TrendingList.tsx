import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { marketApi } from '../../api/market';
import type { HotStock } from '../../types';
import { TrendingUp } from 'lucide-react';

const TrendingList: React.FC = () => {
    const navigate = useNavigate();
    const { data: stocks, isLoading, error } = useQuery<HotStock[]>({
        queryKey: ['hotRank'],
        queryFn: () => marketApi.getHotRank(10), // Get top 10
        refetchInterval: 60000, // Refresh every minute
    });

    if (isLoading) return <div className="p-4 text-center text-gray-500">Loading Trends...</div>;
    if (error) return <div className="p-4 text-center text-red-500">Failed to load trends</div>;

    return (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
            <div className="flex items-center mb-3">
                <TrendingUp className="w-5 h-5 text-red-500 mr-2" />
                <h2 className="text-lg font-bold text-gray-800">Trending Stocks</h2>
            </div>

            <div className="flex flex-col gap-3">
                {stocks?.map((stock) => (
                    <div
                        key={stock.code}
                        onClick={() => navigate(`/stock/${stock.code}`)}
                        className="glass-card flex items-center justify-between"
                    >
                        <div className="flex items-center gap-4">
                            <div className="flex flex-col">
                                <span className="text-base font-bold">{stock.name}</span>
                                <span className="text-xs text-secondary font-mono tracking-wide">{stock.code}</span>
                            </div>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-base font-bold tabular-nums">{stock.price.toFixed(2)}</span>
                            <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${stock.change_percent >= 0
                                ? 'bg-success bg-opacity-10 price-up'
                                : 'bg-danger bg-opacity-10 price-down'
                                }`}>
                                {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TrendingList;
