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
        <div className="app-container">
            {/* Header with Search */}
            <header className="safe-area-top bg-opacity-90 backdrop-blur-md sticky top-0 z-10 p-5 flex flex-col gap-4">
                <div className="flex items-center gap-4">
                    <button onClick={() => navigate(-1)} className="p-2 -ml-2">
                        <ArrowLeft className="w-6 h-6 text-white" />
                    </button>
                    <h1 className="text-2xl text-gradient">智能选股</h1>
                </div>

                <form onSubmit={handleSearch} className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-secondary group-focus-within:text-primary transition-colors" />
                    </div>
                    <input
                        type="text"
                        className="block w-full bg-card border border-border rounded-2xl py-4 pl-12 pr-12 text-sm text-white placeholder-text-tertiary focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                        placeholder="输入选股指令, 如: ROE>20% 且 增长>30%"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                        {isPending ? (
                            <Loader2 className="h-5 w-5 text-primary animate-spin" />
                        ) : (
                            <button type="submit" className="text-primary font-bold text-sm">搜索</button>
                        )}
                    </div>
                </form>
            </header>

            {/* Content */}
            <div className="flex-1 px-5 pb-8 overflow-auto">
                {error && (
                    <div className="bg-danger bg-opacity-10 border border-danger border-opacity-20 rounded-xl p-4 text-danger text-sm flex items-center gap-3">
                        <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
                        搜索失败: {error.message}
                    </div>
                )}

                {!data && !isPending && !error && (
                    <div className="flex flex-col items-center justify-center pt-24 gap-6 opacity-40">
                        <div className="p-8 rounded-full bg-border">
                            <Search className="w-12 h-12 text-secondary" />
                        </div>
                        <div className="text-center">
                            <p className="text-base font-semibold">想搜索什么？</p>
                            <p className="text-xs mt-1 italic">"今日涨停个股" 或 "近期主力净买入前10"</p>
                        </div>
                    </div>
                )}

                {data && (
                    <div className="mt-4 flex flex-col gap-4">
                        <div className="flex justify-between items-center px-1">
                            <span className="text-xs text-secondary">搜索结果 ({data.data.length})</span>
                            <span className="text-[10px] text-tertiary">滑动以查看详情</span>
                        </div>

                        <div className="glass-card shadow-xl overflow-hidden p-0">
                            <div className="overflow-x-auto no-scrollbar">
                                <table className="w-full text-xs text-left">
                                    <thead className="text-[10px] text-secondary uppercase tracking-wider bg-white bg-opacity-5">
                                        <tr>
                                            {data.columns.map((col, idx) => (
                                                <th key={idx} className="px-5 py-4 font-bold border-b border-border">{col}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                        {data.data.map((row, rIdx) => {
                                            const code = findCode(row, data.columns);
                                            return (
                                                <tr
                                                    key={rIdx}
                                                    className={`transition-colors active:bg-white active:bg-opacity-5 ${code ? 'cursor-pointer' : ''}`}
                                                    onClick={() => code && navigate(`/stock/${code}`)}
                                                >
                                                    {row.map((cell, cIdx: number) => (
                                                        <td key={cIdx} className="px-5 py-4 whitespace-nowrap max-w-[200px] truncate tabular-nums">
                                                            {typeof cell === 'object' ? JSON.stringify(cell) : String(cell)}
                                                        </td>
                                                    ))}
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <BottomNav />
        </div>
    );
};

export default SmartScreener;
