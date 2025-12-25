import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { useQuery } from '@tanstack/react-query';
import { stockApi } from '../../api/stock';
import type { KLineData } from '../../types';

interface KlineChartProps {
    code: string;
}

const KlineChart: React.FC<KlineChartProps> = ({ code }) => {
    const chartRef = useRef<HTMLDivElement>(null);
    const chartInstance = useRef<echarts.ECharts | null>(null);

    const { data: klineData, isLoading } = useQuery<KLineData[]>({
        queryKey: ['kline', code],
        queryFn: () => stockApi.getKline(code),
        enabled: !!code,
    });

    useEffect(() => {
        if (chartRef.current) {
            chartInstance.current = echarts.init(chartRef.current);
        }

        // Resize handler
        const handleResize = () => chartInstance.current?.resize();
        window.addEventListener('resize', handleResize);

        return () => {
            chartInstance.current?.dispose();
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    useEffect(() => {
        if (!klineData || !chartInstance.current) return;

        const dates = klineData.map(item => item.date);
        const data = klineData.map(item => [
            parseFloat(item.open),
            parseFloat(item.close),
            parseFloat(item.low),
            parseFloat(item.high)
        ]);

        // Calculate distinct colors
        const upColor = '#ef4444';
        const downColor = '#22c55e';

        const option: echarts.EChartsOption = {
            backgroundColor: '#fff',
            animation: false,
            legend: {
                bottom: 10,
                left: 'center',
                data: ['Daily K']
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' }
            },
            grid: {
                left: '10%',
                right: '10%',
                bottom: '15%'
            },
            xAxis: {
                type: 'category',
                data: dates,
                boundaryGap: false,
                axisLine: { onZero: false },
                splitLine: { show: false },
                min: 'dataMin',
                max: 'dataMax'
            },
            yAxis: {
                scale: true,
                splitArea: { show: true }
            },
            dataZoom: [
                { type: 'inside', start: 50, end: 100 },
                { show: true, type: 'slider', top: '90%', start: 50, end: 100 }
            ],
            series: [
                {
                    name: 'Daily K',
                    type: 'candlestick',
                    data: data,
                    itemStyle: {
                        color: upColor,
                        color0: downColor,
                        borderColor: upColor,
                        borderColor0: downColor
                    }
                }
            ]
        };

        chartInstance.current.setOption(option);
    }, [klineData]);

    if (isLoading) return <div className="h-64 flex items-center justify-center text-gray-400">Loading Chart...</div>;

    return <div ref={chartRef} className="w-full h-80 bg-white" />;
};

export default KlineChart;
