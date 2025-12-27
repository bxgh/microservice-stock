import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { consoleApi } from '../api/console';
import BottomNav from '../components/layout/BottomNav';
import { ArrowLeft, Play, Pause, RefreshCw, Activity } from 'lucide-react';

const Console: React.FC = () => {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // Fetch jobs
    const { data, isLoading } = useQuery({
        queryKey: ['scheduler-jobs'],
        queryFn: consoleApi.getJobs,
        refetchInterval: 5000,
    });

    // Mutations
    const runMutation = useMutation({ mutationFn: consoleApi.runJob, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler-jobs'] }) });
    const pauseMutation = useMutation({ mutationFn: consoleApi.pauseJob, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler-jobs'] }) });
    const resumeMutation = useMutation({ mutationFn: consoleApi.resumeJob, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduler-jobs'] }) });

    return (
        <div className="app-container">
            {/* Header */}
            <header className="safe-area-top bg-opacity-90 backdrop-blur-md sticky top-0 z-10 px-6 py-4 flex items-center gap-4">
                <button onClick={() => navigate(-1)} className="p-1 -ml-2">
                    <ArrowLeft className="w-6 h-6" />
                </button>
                <h1 className="text-2xl text-gradient">系统运维</h1>
            </header>

            <div className="px-5 py-4 flex flex-col gap-6">
                {/* Server Status Header */}
                <div className="flex justify-between items-center bg-card border border-border rounded-2xl p-5">
                    <div className="flex flex-col">
                        <span className="text-secondary text-[10px] uppercase font-bold tracking-widest">Server Status</span>
                        <div className="flex items-center gap-2 mt-1">
                            <div className="w-2 h-2 rounded-full bg-success shadow-[0_0_8px_var(--success)]" />
                            <span className="text-base font-bold">运行中</span>
                        </div>
                    </div>
                    <RefreshCw className={`w-5 h-5 text-secondary ${isLoading ? 'animate-spin' : ''}`} />
                </div>

                {/* Task List */}
                <section className="flex flex-col gap-4">
                    <h2 className="text-lg px-1">调度任务 ({data?.jobs.length || 0})</h2>

                    <div className="flex flex-col gap-3">
                        {data?.jobs.map((job) => (
                            <div key={job.id} className="glass-card flex flex-col gap-4 p-5">
                                <div className="flex justify-between items-start">
                                    <div className="flex flex-col gap-1">
                                        <div className="flex items-center gap-2">
                                            <Activity className="w-4 h-4 text-primary" />
                                            <span className="font-bold text-sm tracking-tight">{job.id}</span>
                                        </div>
                                        <span className="text-[10px] text-tertiary">Trigger: {job.trigger}</span>
                                    </div>
                                    <div className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${job.next_run_time ? 'bg-success bg-opacity-10 text-success' : 'bg-warning bg-opacity-10 text-warning'
                                        }`}>
                                        {job.next_run_time ? 'ACTIVE' : 'PAUSED'}
                                    </div>
                                </div>

                                <div className="flex flex-col gap-1 bg-white bg-opacity-5 rounded-xl p-3">
                                    <span className="text-[10px] text-secondary font-medium">NEXT RUN</span>
                                    <span className="text-xs font-mono">
                                        {job.next_run_time ? new Date(job.next_run_time).toLocaleString() : '等待触发'}
                                    </span>
                                </div>

                                <div className="flex gap-2">
                                    <button
                                        onClick={() => runMutation.mutate(job.id)}
                                        disabled={runMutation.isPending}
                                        className="flex-1 bg-primary bg-opacity-10 text-primary py-3 rounded-xl flex items-center justify-center gap-2 active:scale-95 transition-transform"
                                    >
                                        <Play className="w-4 h-4 fill-current" />
                                        <span className="text-xs font-bold">执行</span>
                                    </button>

                                    {job.next_run_time ? (
                                        <button
                                            onClick={() => pauseMutation.mutate(job.id)}
                                            className="flex-1 bg-warning bg-opacity-10 text-warning py-3 rounded-xl flex items-center justify-center gap-2 active:scale-95 transition-transform"
                                        >
                                            <Pause className="w-4 h-4 fill-current" />
                                            <span className="text-xs font-bold">暂停</span>
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => resumeMutation.mutate(job.id)}
                                            className="flex-1 bg-success bg-opacity-10 text-success py-3 rounded-xl flex items-center justify-center gap-2 active:scale-95 transition-transform"
                                        >
                                            <Play className="w-4 h-4 fill-current" />
                                            <span className="text-xs font-bold">恢复</span>
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </div>

            <BottomNav />
        </div>
    );
};

export default Console;
