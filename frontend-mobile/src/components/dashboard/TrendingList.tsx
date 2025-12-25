import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { marketApi } from '../../api/market';
import type { HotStock } from '../../types';
import { TrendingUp, ArrowUp, ArrowDown } from 'lucide-react';

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

            <div className="space-y-3">
                {stocks?.map((stock, index) => (
                    <div
                        key={stock.code}
                        onClick={() => navigate(`/stock/${stock.code}`)}
                        className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0 cursor-pointer"
                    >
                        <div className="flex items-center">
                            <span className={`w-5 h-5 flex items-center justify-center text-xs rounded-full mr-3 ${index < 3 ? 'bg-red-100 text-red-600 font-bold' : 'bg-gray-100 text-gray-500'}`}>
                                {index + 1}
                            </span>
                            <div>
                                <div className="font-medium text-gray-900">{stock.name}</div>
                                <div className="text-xs text-gray-400">{stock.code}</div>
                            </div>
                        </div>

                        {/* Note: Adjust API might return different field names, assuming change_percent for now */}
                        <div className={`flex items-center font-medium ${stock.change_percent >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                            {stock.change_percent > 0 ? <ArrowUp className="w-3 h-3 mr-1" /> : <ArrowDown className="w-3 h-3 mr-1" />}
                            {Math.abs(stock.change_percent).toFixed(2)}%
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TrendingList;
