/**
 * Chart Types
 * 
 * TypeScript definitions for chart components
 */

// Candlestick/OHLC Data
export interface CandlestickData {
  time: string | number;  // ISO date string or Unix timestamp
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

// Performance/Line Chart Data
export interface PerformanceData {
  date: string;
  value: number;
  benchmark?: number;
  label?: string;
}

// Allocation/Pie Chart Data
export interface AllocationData {
  name: string;
  value: number;
  color?: string;
  percentage?: number;
}

// Volume Data
export interface VolumeData {
  time: string | number;
  value: number;
  color?: string;
}

// Drawdown Data
export interface DrawdownData {
  date: string;
  drawdown: number;
  peak?: number;
  value?: number;
}

// Risk Data
export interface RiskData {
  date: string;
  var95: number;
  var99?: number;
  cvar?: number;
  volatility?: number;
}

// Chart Timeframes
export type ChartTimeframe = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL';

// Chart Theme
export interface ChartTheme {
  backgroundColor: string;
  textColor: string;
  gridColor: string;
  upColor: string;
  downColor: string;
  borderUpColor: string;
  borderDownColor: string;
  wickUpColor: string;
  wickDownColor: string;
  volumeUpColor: string;
  volumeDownColor: string;
  crosshairColor: string;
}

// Default Themes
export const lightTheme: ChartTheme = {
  backgroundColor: '#ffffff',
  textColor: '#333333',
  gridColor: '#e0e0e0',
  upColor: '#22c55e',
  downColor: '#ef4444',
  borderUpColor: '#16a34a',
  borderDownColor: '#dc2626',
  wickUpColor: '#16a34a',
  wickDownColor: '#dc2626',
  volumeUpColor: 'rgba(34, 197, 94, 0.5)',
  volumeDownColor: 'rgba(239, 68, 68, 0.5)',
  crosshairColor: '#9ca3af',
};

export const darkTheme: ChartTheme = {
  backgroundColor: '#1a1a2e',
  textColor: '#e0e0e0',
  gridColor: '#2a2a4a',
  upColor: '#22c55e',
  downColor: '#ef4444',
  borderUpColor: '#16a34a',
  borderDownColor: '#dc2626',
  wickUpColor: '#16a34a',
  wickDownColor: '#dc2626',
  volumeUpColor: 'rgba(34, 197, 94, 0.5)',
  volumeDownColor: 'rgba(239, 68, 68, 0.5)',
  crosshairColor: '#6b7280',
};

// Chart Props Common Interface
export interface BaseChartProps {
  width?: number | string;
  height?: number;
  theme?: 'light' | 'dark';
  loading?: boolean;
  error?: string;
  className?: string;
}

// Candlestick Chart Props
export interface CandlestickChartProps extends BaseChartProps {
  data: CandlestickData[];
  symbol?: string;
  showVolume?: boolean;
  showMA?: boolean;
  maLength?: number;
  onCrosshairMove?: (data: CandlestickData | null) => void;
}

// Performance Chart Props
export interface PerformanceChartProps extends BaseChartProps {
  data: PerformanceData[];
  showBenchmark?: boolean;
  benchmarkLabel?: string;
  valueLabel?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
  areaFill?: boolean;
}

// Allocation Chart Props
export interface AllocationChartProps extends BaseChartProps {
  data: AllocationData[];
  showLabels?: boolean;
  showLegend?: boolean;
  innerRadius?: number;
  outerRadius?: number;
  animate?: boolean;
  currency?: string;  // Currency for value display
}

// Volume Chart Props
export interface VolumeChartProps extends BaseChartProps {
  data: VolumeData[];
  barWidth?: number;
}

// Drawdown Chart Props
export interface DrawdownChartProps extends BaseChartProps {
  data: DrawdownData[];
  showWatermark?: boolean;
  fillColor?: string;
}

// Risk Chart Props
export interface RiskChartProps extends BaseChartProps {
  data: RiskData[];
  showVar99?: boolean;
  showCvar?: boolean;
  showVolatility?: boolean;
}

// Tooltip Data
export interface TooltipData {
  label: string;
  value: number | string;
  color?: string;
}

// Legend Item
export interface LegendItem {
  label: string;
  color: string;
  value?: number | string;
  active?: boolean;
}
