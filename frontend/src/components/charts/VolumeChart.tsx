/**
 * VolumeChart Component
 * 
 * Standalone volume bar chart
 */
import React, { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  HistogramData,
  UTCTimestamp,
} from 'lightweight-charts';
import { clsx } from 'clsx';
import type { VolumeChartProps, VolumeData } from './types';
import { lightTheme, darkTheme } from './types';

const convertToHistogram = (data: VolumeData[]): HistogramData[] => {
  return data.map((d) => ({
    time: (typeof d.time === 'string'
      ? Math.floor(new Date(d.time).getTime() / 1000)
      : d.time) as UTCTimestamp,
    value: d.value,
    color: d.color,
  }));
};

export const VolumeChart: React.FC<VolumeChartProps> = ({
  data,
  width = '100%',
  height = 150,
  theme = 'light',
  loading = false,
  error,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);

  const chartTheme = theme === 'dark' ? darkTheme : lightTheme;

  useEffect(() => {
    if (!containerRef.current || loading || error) return;

    const chart = createChart(containerRef.current, {
      width: typeof width === 'number' ? width : containerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: ColorType.Solid, color: chartTheme.backgroundColor },
        textColor: chartTheme.textColor,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: chartTheme.gridColor },
      },
      rightPriceScale: {
        borderColor: chartTheme.gridColor,
      },
      timeScale: {
        borderColor: chartTheme.gridColor,
        visible: true,
      },
    });

    chartRef.current = chart;

    const volumeSeries = chart.addHistogramSeries({
      color: chartTheme.volumeUpColor,
      priceFormat: {
        type: 'volume',
      },
    });
    seriesRef.current = volumeSeries;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [loading, error, theme]);

  useEffect(() => {
    if (!seriesRef.current || data.length === 0) return;

    const histogramData = convertToHistogram(data);
    seriesRef.current.setData(histogramData);

    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  if (error) {
    return (
      <div className={clsx('flex items-center justify-center text-gray-500', className)} style={{ height }}>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className={clsx('relative', className)}>
      <div ref={containerRef} className="w-full" />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
        </div>
      )}
    </div>
  );
};

export default VolumeChart;
