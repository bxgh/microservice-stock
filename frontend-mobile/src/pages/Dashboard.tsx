import React from 'react';
import TrendingList from '../components/dashboard/TrendingList';
import SectorGrid from '../components/dashboard/SectorGrid';
import BottomNav from '../components/layout/BottomNav';

const Dashboard: React.FC = () => {
    return (
        <div className="min-h-screen bg-gray-100 pb-20">
            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 sticky top-0 z-10">
                <h1 className="text-xl font-bold text-gray-900">Market Overview</h1>
            </header>

            {/* Content */}
            <main className="p-4">
                {/* Hot Sectors */}
                <SectorGrid />

                {/* Trending Stocks */}
                <TrendingList />
            </main>

            <BottomNav />
        </div>
    );
};

export default Dashboard;
