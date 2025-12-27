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

            <div className="flex overflow-x-auto gap-4 py-2 no-scrollbar -mx-5 px-5">
                {sectors?.map((sector) => (
                    <div key={sector.name} className="flex-shrink-0 w-32 glass-card flex flex-col gap-2">
                        <span className="text-xs text-secondary font-medium truncate">{sector.name}</span>
                        <span className={`text-lg font-bold ${sector.change_percent >= 0 ? 'price-up' : 'price-down'}`}>
                            {sector.change_percent >= 0 ? '+' : ''}{sector.change_percent.toFixed(2)}%
                        </span>
                        <div className={`h-1 w-full rounded-full bg-opacity-20 ${sector.change_percent >= 0 ? 'bg-success' : 'bg-danger'}`}>
                            <div
                                className={`h-full rounded-full ${sector.change_percent >= 0 ? 'bg-success' : 'bg-danger'}`}
                                style={{ width: `${Math.min(Math.abs(sector.change_percent) * 20, 100)}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SectorGrid;
