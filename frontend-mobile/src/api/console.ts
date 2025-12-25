import { apiClient } from './client';
import type { SchedulerJob } from '../types';

export const consoleApi = {
    // Get all jobs
    getJobs: async (): Promise<{ total: number; jobs: SchedulerJob[] }> => {
        return apiClient.get('/baostock/scheduler/jobs');
    },

    // Pause Job
    pauseJob: async (jobId: string): Promise<{ message: string }> => {
        return apiClient.post(`/baostock/scheduler/jobs/${jobId}/pause`);
    },

    // Resume Job
    resumeJob: async (jobId: string): Promise<{ message: string }> => {
        return apiClient.post(`/baostock/scheduler/jobs/${jobId}/resume`);
    },

    // Run Job Immediately
    runJob: async (jobId: string): Promise<{ message: string }> => {
        return apiClient.post(`/baostock/scheduler/jobs/${jobId}/run`);
    }
};
