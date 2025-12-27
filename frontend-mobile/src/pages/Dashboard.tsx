import React from 'react';
import TrendingList from '../components/dashboard/TrendingList';
import SectorGrid from '../components/dashboard/SectorGrid';
import BottomNav from '../components/layout/BottomNav';

const Dashboard: React.FC = () => {
    return (
        <div className="app-container">
            {/* Header */}
            <header className="safe-area-top px-6 py-4 flex flex-col gap-1 sticky top-0 z-10 bg-deep bg-opacity-90 backdrop-blur-md">
                <span className="text-secondary text-xs font-semibold tracking-wider uppercase">Market Data</span>
                <h1 className="text-3xl text-gradient">市场概览</h1>
            </header>

            {/* Content */}
            <main className="px-5 py-4 flex flex-col gap-8">
                {/* Hot Sectors */}
                <section>
                    <div className="flex justify-between items-end mb-4 px-1">
                        <h2 className="text-lg">热门板块</h2>
                        <span className="text-primary text-xs font-semibold">查看全部</span>
                    </div>
                    <SectorGrid />
                </section>

                {/* Trending Stocks */}
                <section>
                    <div className="flex justify-between items-end mb-4 px-1">
                        <h2 className="text-lg">今日热榜</h2>
                        <div className="bg-success bg-opacity-10 text-success text-[10px] px-2 py-0.5 rounded-full font-bold">
                            LIVE
                        </div>
                    </div>
                    <TrendingList />
                </section>
            </main>

            <BottomNav />
        </div>
    );
};

export default Dashboard;
