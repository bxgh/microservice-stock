import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import KlineChart from '../components/stock/KlineChart';
import FundamentalInfo from '../components/stock/FundamentalInfo';
import { ArrowLeft } from 'lucide-react';

const StockDetail: React.FC = () => {
    const { code } = useParams<{ code: string }>();
    const navigate = useNavigate();

    if (!code) return <div>Invalid Code</div>;

    return (
        <div className="min-h-screen bg-gray-100 pb-20">
            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 sticky top-0 z-10 flex items-center">
                <button onClick={() => navigate(-1)} className="mr-4">
                    <ArrowLeft className="w-5 h-5 text-gray-600" />
                </button>
                <h1 className="text-lg font-bold text-gray-900">{code}</h1>
            </header>

            {/* Content */}
            <div className="p-4">
                {/* Chart */}
                <div className="bg-white rounded-lg shadow-sm p-2 mb-4">
                    <KlineChart code={code} />
                </div>

                {/* Info */}
                <FundamentalInfo code={code} />
            </div>
        </div>
    );
};

export default StockDetail;
