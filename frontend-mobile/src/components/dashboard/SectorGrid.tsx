import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { marketApi } from '../../api/market';
import type { Sector } from '../../types';
import { Layers } from 'lucide-react';

const SectorGrid: React.FC = () => {
    const { data: sectors, isLoading, error } = useQuery<Sector[]>({
        queryKey: ['hotSectors'],
        queryFn: () => marketApi.getHotSectors(6), // Get top 6
        refetchInterval: 60000,
    });

    if (isLoading) return <div className="p-4 text-center text-gray-500">Loading Sectors...</div>;
    if (error) return <div className="p-4 text-center text-red-500">Failed to load sectors</div>;

    return (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
            <div className="flex items-center mb-3">
                <Layers className="w-5 h-5 text-blue-500 mr-2" />
                <h2 className="text-lg font-bold text-gray-800">Hot Sectors</h2>
            </div>

            <div className="grid grid-cols-2 gap-3">
                {sectors?.map((sector) => (
                    <div key={sector.name} className="bg-gray-50 rounded-md p-3 flex flex-col justify-between">
                        <div className="text-sm font-medium text-gray-700 truncate">{sector.name}</div>
                        <div className={`text-lg font-bold mt-1 ${sector.change_percent >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                            {sector.change_percent > 0 ? '+' : ''}{sector.change_percent.toFixed(2)}%
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SectorGrid;
