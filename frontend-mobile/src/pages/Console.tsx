import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { consoleApi } from '../api/console';
import BottomNav from '../components/layout/BottomNav';
import { ArrowLeft, Play, Pause, RefreshCw, Activity } from 'lucide-react';

const Console: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // Fetch Jobs
    const { data, isLoading } = useQuery({
        queryKey: ['jobs'],
        queryFn: consoleApi.getJobs,
        refetchInterval: 5000, // Refresh status every 5s
    });

    // Actions
    const pauseMutation = useMutation({
        mutationFn: consoleApi.pauseJob,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] })
    });

    const resumeMutation = useMutation({
        mutationFn: consoleApi.resumeJob,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] })
    });

    const runMutation = useMutation({
        mutationFn: consoleApi.runJob,
        onSuccess: () => alert('任务已触发后台运行')
    });

    if (isLoading) return <div className="p-10 text-center">Loading Console...</div>;

    return (
        <div className="min-h-screen bg-gray-100 flex flex-col">
            {/* Header */}
            <header className="bg-white shadow-sm px-4 py-3 sticky top-0 z-10 flex items-center bg-gray-900 text-white">
                <button onClick={() => navigate(-1)} className="mr-3">
                    <ArrowLeft className="w-5 h-5 text-gray-400" />
                </button>
                <h1 className="text-lg font-bold flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-green-500" />
                    Ops Console
                </h1>
            </header>

            {/* Content */}
            <div className="p-4 space-y-4">
                <div className="bg-white rounded-lg shadow-sm p-4">
                    <h2 className="text-sm font-bold text-gray-500 uppercase mb-3">Scheduler Jobs ({data?.total || 0})</h2>
                    <div className="space-y-3">
                        {data?.jobs.map((job) => {
                            // Note: APScheduler doesn't return 'paused' state directly in get_jobs usually unless checked, 
                            // but if next_run_time is None, it's likely paused or finished.

                            return (
                                <div key={job.id} className="border border-gray-100 rounded-md p-3">
                                    <div className="flex justify-between items-start mb-2">
                                        <div>
                                            <div className="font-bold text-gray-800 text-sm">{job.name}</div>
                                            <div className="text-xs text-gray-400 font-mono mt-1">{job.id}</div>
                                        </div>
                                        <div className={`text-xs px-2 py-1 rounded ${job.next_run_time ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'}`}>
                                            {job.next_run_time ? 'Active' : 'Paused'}
                                        </div>
                                    </div>

                                    <div className="text-xs text-gray-500 mb-3">
                                        Next Run: {job.next_run_time || 'No Schedule'}
                                    </div>

                                    <div className="flex space-x-2">
                                        {/* Run Now */}
                                        <button
                                            onClick={() => runMutation.mutate(job.id)}
                                            disabled={runMutation.isPending}
                                            className="flex-1 bg-blue-50 text-blue-600 text-xs py-2 rounded flex items-center justify-center font-medium active:bg-blue-100"
                                        >
                                            <Play className="w-3 h-3 mr-1" /> Run Now
                                        </button>

                                        {/* Pause/Resume */}
                                        {job.next_run_time ? (
                                            <button
                                                onClick={() => pauseMutation.mutate(job.id)}
                                                className="flex-1 bg-gray-50 text-gray-600 text-xs py-2 rounded flex items-center justify-center font-medium active:bg-gray-100"
                                            >
                                                <Pause className="w-3 h-3 mr-1" /> Pause
                                            </button>
                                        ) : (
                                            <button
                                                onClick={() => resumeMutation.mutate(job.id)}
                                                className="flex-1 bg-green-50 text-green-600 text-xs py-2 rounded flex items-center justify-center font-medium active:bg-green-100"
                                            >
                                                <RefreshCw className="w-3 h-3 mr-1" /> Resume
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            <BottomNav />
        </div>
    );
};

export default Console;
