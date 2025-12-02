/**
 * CandlestickChart Component
 * 
 * Professional candlestick chart using TradingView Lightweight Charts:
 * - OHLC candlesticks
 * - Volume bars
 * - Moving average overlay
 * - Crosshair with data display
 * - Light/Dark theme support
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  CandlestickData as LWCandlestickData,
  HistogramData,
  LineData,
  UTCTimestamp,
} from 'lightweight-charts';
import { clsx } from 'clsx';
import type { CandlestickChartProps, CandlestickData, ChartTheme } from './types';
import { lightTheme, darkTheme } from './types';

// Convert our data format to lightweight-charts format
const convertToLWCandlestick = (data: CandlestickData[]): LWCandlestickData[] => {
  return data.map((d) => ({
    time: (typeof d.time === 'string' 
      ? Math.floor(new Date(d.time).getTime() / 1000) 
      : d.time) as UTCTimestamp,
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }));
};

// Convert volume data
const convertToVolume = (
  data: CandlestickData[],
  upColor: string,
  downColor: string
): HistogramData[] => {
  return data
    .filter((d) => d.volume !== undefined)
    .map((d) => ({
      time: (typeof d.time === 'string'
        ? Math.floor(new Date(d.time).getTime() / 1000)
        : d.time) as UTCTimestamp,
      value: d.volume!,
      color: d.close >= d.open ? upColor : downColor,
    }));
};

// Calculate Simple Moving Average
const calculateSMA = (data: CandlestickData[], period: number): LineData[] => {
  const sma: LineData[] = [];
  
  for (let i = period - 1; i < data.length; i++) {
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += data[i - j].close;
    }
    sma.push({
      time: (typeof data[i].time === 'string'
        ? Math.floor(new Date(data[i].time).getTime() / 1000)
        : data[i].time) as UTCTimestamp,
      value: sum / period,
    });
  }
  
  return sma;
};

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  symbol = '',
  showVolume = true,
  showMA = true,
  maLength = 20,
  width = '100%',
  height = 400,
  theme = 'light',
  loading = false,
  error,
  className,
  onCrosshairMove,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  
  const [currentData, setCurrentData] = useState<CandlestickData | null>(null);

  const chartTheme: ChartTheme = theme === 'dark' ? darkTheme : lightTheme;

  // Initialize chart
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
        vertLines: { color: chartTheme.gridColor },
        horzLines: { color: chartTheme.gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: chartTheme.crosshairColor,
          width: 1,
          style: 3,
          labelBackgroundColor: chartTheme.textColor,
        },
        horzLine: {
          color: chartTheme.crosshairColor,
          width: 1,
          style: 3,
          labelBackgroundColor: chartTheme.textColor,
        },
      },
      rightPriceScale: {
        borderColor: chartTheme.gridColor,
      },
      timeScale: {
        borderColor: chartTheme.gridColor,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: chartTheme.upColor,
      downColor: chartTheme.downColor,
      borderUpColor: chartTheme.borderUpColor,
      borderDownColor: chartTheme.borderDownColor,
      wickUpColor: chartTheme.wickUpColor,
      wickDownColor: chartTheme.wickDownColor,
    });
    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series if enabled
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: chartTheme.volumeUpColor,
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'volume',
      });
      
      chart.priceScale('volume').applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });
      
      volumeSeriesRef.current = volumeSeries;
    }

    // Add MA series if enabled
    if (showMA) {
      const maSeries = chart.addLineSeries({
        color: '#2563eb',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      maSeriesRef.current = maSeries;
    }

    // Subscribe to crosshair move
    chart.subscribeCrosshairMove((param) => {
      if (param.time && param.seriesData.size > 0) {
        const candleData = param.seriesData.get(candlestickSeries);
        if (candleData && 'open' in candleData) {
          const dataPoint: CandlestickData = {
            time: param.time as number,
            open: candleData.open,
            high: candleData.high,
            low: candleData.low,
            close: candleData.close,
          };
          setCurrentData(dataPoint);
          onCrosshairMove?.(dataPoint);
        }
      } else {
        setCurrentData(null);
        onCrosshairMove?.(null);
      }
    });

    // Handle resize
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
      chartRef.current = null;
      candlestickSeriesRef.current = null;
      volumeSeriesRef.current = null;
      maSeriesRef.current = null;
    };
  }, [loading, error, theme, showVolume, showMA]);

  // Update data
  useEffect(() => {
    if (!candlestickSeriesRef.current || data.length === 0) return;

    const candlestickData = convertToLWCandlestick(data);
    candlestickSeriesRef.current.setData(candlestickData);

    if (volumeSeriesRef.current && showVolume) {
      const volumeData = convertToVolume(
        data,
        chartTheme.volumeUpColor,
        chartTheme.volumeDownColor
      );
      volumeSeriesRef.current.setData(volumeData);
    }

    if (maSeriesRef.current && showMA && data.length >= maLength) {
      const smaData = calculateSMA(data, maLength);
      maSeriesRef.current.setData(smaData);
    }

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data, showVolume, showMA, maLength, chartTheme]);

  // Format price change
  const formatPriceChange = useCallback((open: number, close: number) => {
    const change = close - open;
    const changePercent = (change / open) * 100;
    return {
      change: change.toFixed(2),
      percent: changePercent.toFixed(2),
      isPositive: change >= 0,
    };
  }, []);

  if (error) {
    return (
      <div className={clsx('flex items-center justify-center', className)} style={{ height }}>
        <div className="text-center text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="mt-2 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('relative', className)}>
      {/* OHLC Display */}
      {currentData && (
        <div className="absolute top-2 left-2 z-10 bg-white/90 dark:bg-gray-800/90 rounded-lg px-3 py-2 shadow-sm">
          <div className="flex items-center gap-4 text-sm">
            {symbol && (
              <span className="font-semibold text-gray-900 dark:text-white">
                {symbol}
              </span>
            )}
            <div className="flex gap-3">
              <span className="text-gray-500 dark:text-gray-400">
                O: <span className="text-gray-900 dark:text-white">{currentData.open.toFixed(2)}</span>
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                H: <span className="text-gray-900 dark:text-white">{currentData.high.toFixed(2)}</span>
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                L: <span className="text-gray-900 dark:text-white">{currentData.low.toFixed(2)}</span>
              </span>
              <span className="text-gray-500 dark:text-gray-400">
                C: <span className="text-gray-900 dark:text-white">{currentData.close.toFixed(2)}</span>
              </span>
            </div>
            {(() => {
              const { change, percent, isPositive } = formatPriceChange(
                currentData.open,
                currentData.close
              );
              return (
                <span className={isPositive ? 'text-green-600' : 'text-red-600'}>
                  {isPositive ? '+' : ''}{change} ({isPositive ? '+' : ''}{percent}%)
                </span>
              );
            })()}
          </div>
        </div>
      )}

      {/* Chart Container */}
      <div ref={containerRef} className="w-full" />

      {/* Legend */}
      {showMA && (
        <div className="absolute bottom-2 left-2 z-10 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span className="w-3 h-0.5 bg-blue-600" />
          <span>SMA({maLength})</span>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-800/80">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}
    </div>
  );
};

export default CandlestickChart;
