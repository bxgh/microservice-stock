import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import KlineChart from '../components/stock/KlineChart';
import FundamentalInfo from '../components/stock/FundamentalInfo';
import { ArrowLeft, TrendingUp } from 'lucide-react';

const StockDetail: React.FC = () => {
    const { code } = useParams<{ code: string }>();
    const navigate = useNavigate();

    if (!code) return <div>Invalid Stock Code</div>;

    return (
        <div className="app-container bg-bg-deep">
            {/* Immersive Header */}
            <header className="safe-area-top px-5 py-4 flex items-center justify-between sticky top-0 z-20 bg-bg-deep bg-opacity-80 backdrop-blur-xl border-b border-white border-opacity-5">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate(-1)} className="p-1 -ml-2">
                        <ArrowLeft className="w-6 h-6" />
                    </button>
                    <div className="flex flex-col">
                        <h1 className="text-xl font-bold tracking-tight">{code}</h1>
                        <span className="text-[10px] text-secondary font-semibold uppercase tracking-widest text-gradient">Stock Analysis</span>
                    </div>
                </div>
                <div className="p-2 rounded-full bg-white bg-opacity-5">
                    <TrendingUp className="w-5 h-5 text-primary" />
                </div>
            </header>

            <main className="flex flex-col gap-6">
                {/* Chart Section - Edge to Edge potential */}
                <section className="bg-card">
                    <KlineChart code={code} />
                </section>

                <div className="px-5 pb-10 flex flex-col gap-8">
                    {/* Metrics Section */}
                    <FundamentalInfo code={code} />
                </div>
            </main>
        </div>
    );
};

export default StockDetail;
