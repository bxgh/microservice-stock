import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { marketApi } from '../api/market';
import { Search, ArrowLeft, Loader2 } from 'lucide-react';
import type { QueryResult } from '../types';
import BottomNav from '../components/layout/BottomNav';

const SmartScreener: React.FC = () => {
    const navigate = useNavigate();
    const [query, setQuery] = useState('');

    // Mutation for search
    const { mutate, isPending, data, error } = useMutation<QueryResult, Error, string>({
        mutationFn: (q) => marketApi.queryStocks(q),
    });

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        mutate(query);
    };

    // Helper to find stock code in a row to enable navigation
    const findCode = (row: (string | number)[], columns: string[]) => {
        const codeIndex = columns.findIndex(c => c === 'code' || c === '股票代码');
        if (codeIndex !== -1) return row[codeIndex];
        return null;
    };

    return (
        <div className="min-h-screen bg-gray-100 flex flex-col">
            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 sticky top-0 z-10 flex items-center">
                <button onClick={() => navigate(-1)} className="mr-3">
                    <ArrowLeft className="w-5 h-5 text-gray-600" />
                </button>
                <form onSubmit={handleSearch} className="flex-1 flex items-center bg-gray-100 rounded-full px-4 py-2">
                    <input
                        type="text"
                        className="flex-1 bg-transparent outline-none text-sm text-gray-800 placeholder-gray-400"
                        placeholder="e.g. ROE>20% and Growth>30%"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    {isPending ? (
                        <Loader2 className="w-4 h-4 text-primary animate-spin ml-2" />
                    ) : (
                        <Search className="w-4 h-4 text-gray-400 ml-2" onClick={() => mutate(query)} />
                    )}
                </form>
            </header>

            {/* Content */}
            <div className="flex-1 p-4 overflow-auto">
                {error && (
                    <div className="text-center text-red-500 mt-10 text-sm">
                        Search failed: {error.message}
                    </div>
                )}

                {!data && !isPending && !error && (
                    <div className="text-center text-gray-400 mt-20 text-sm">
                        Try searching for stocks with natural language.<br />
                        Ex: "MACD Golden Cross"
                    </div>
                )}

                {data && (
                    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                        <div className="p-3 border-b border-gray-100 text-sm font-bold text-gray-700">
                            Results ({data.data.length})
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm text-left">
                                <thead className="text-xs text-gray-500 uppercase bg-gray-50">
                                    <tr>
                                        {data.columns.map((col, idx) => (
                                            <th key={idx} className="px-4 py-3 whitespace-nowrap">{col}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.data.map((row, rIdx) => {
                                        const code = findCode(row, data.columns);
                                        return (
                                            <tr
                                                key={rIdx}
                                                className={`border-b border-gray-50 hover:bg-gray-50 ${code ? 'cursor-pointer' : ''}`}
                                                onClick={() => code && navigate(`/stock/${code}`)}
                                            >
                                                {row.map((cell, cIdx: number) => (
                                                    <td key={cIdx} className="px-4 py-3 whitespace-nowrap max-w-xs truncate">
                                                        {typeof cell === 'object' ? JSON.stringify(cell) : cell}
                                                    </td>
                                                ))}
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>

            <BottomNav />
        </div>
    );
};

export default SmartScreener;
