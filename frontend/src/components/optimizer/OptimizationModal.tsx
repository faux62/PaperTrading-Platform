// Optimization Request Modal

import React, { useState } from 'react';
import { 
  X, 
  Sparkles, 
  Settings2,
  ChevronDown,
  ChevronUp,
  Info
} from 'lucide-react';
import type { 
  OptimizationMethodInfo, 
  OptimizationMethod,
  OptimizationRequest 
} from '../../types/optimizer';

interface Props {
  methods: OptimizationMethodInfo[];
  riskProfile: string;
  isOptimizing: boolean;
  onOptimize: (request: OptimizationRequest) => void;
  onClose: () => void;
}

const OptimizationModal: React.FC<Props> = ({
  methods,
  riskProfile,
  isOptimizing,
  onOptimize,
  onClose,
}) => {
  const [selectedMethod, setSelectedMethod] = useState<OptimizationMethod | undefined>();
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [minPositions, setMinPositions] = useState(5);
  const [maxPositions, setMaxPositions] = useState(25);
  const [maxWeightPerAsset, setMaxWeightPerAsset] = useState(0.20);
  const [customUniverse, setCustomUniverse] = useState('');
  const [excludedSymbols, setExcludedSymbols] = useState('');

  const recommendedMethods = methods.filter(m => 
    m.risk_profiles.includes(riskProfile as any)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const request: OptimizationRequest = {
      portfolio_id: '', // Will be set by parent
      method: selectedMethod,
      min_positions: minPositions,
      max_positions: maxPositions,
      max_weight_per_asset: maxWeightPerAsset,
    };

    if (customUniverse.trim()) {
      request.universe = customUniverse.split(',').map(s => s.trim().toUpperCase());
    }

    if (excludedSymbols.trim()) {
      request.excluded_symbols = excludedSymbols.split(',').map(s => s.trim().toUpperCase());
    }

    onOptimize(request);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl 
                    w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b 
                      border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                New Optimization
              </h2>
              <p className="text-xs text-gray-500">Configure and run portfolio optimization</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                     rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="p-4 space-y-6">
            {/* Method Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Optimization Method
              </label>
              
              {/* Recommended */}
              <p className="text-xs text-gray-500 mb-2">
                Recommended for {riskProfile} profile:
              </p>
              <div className="space-y-2 mb-4">
                {recommendedMethods.map((method) => (
                  <label
                    key={method.id}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer
                      ${selectedMethod === method.id 
                        ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                        : 'border-gray-200 dark:border-gray-700 hover:border-purple-300'}`}
                  >
                    <input
                      type="radio"
                      name="method"
                      value={method.id}
                      checked={selectedMethod === method.id}
                      onChange={() => setSelectedMethod(method.id)}
                      className="mt-1 text-purple-600"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {method.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {method.description}
                      </p>
                    </div>
                  </label>
                ))}
              </div>

              {/* Other methods */}
              {methods.filter(m => !m.risk_profiles.includes(riskProfile as any)).length > 0 && (
                <>
                  <p className="text-xs text-gray-500 mb-2">Other methods:</p>
                  <div className="space-y-2">
                    {methods.filter(m => !m.risk_profiles.includes(riskProfile as any)).map((method) => (
                      <label
                        key={method.id}
                        className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer
                          ${selectedMethod === method.id 
                            ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'}`}
                      >
                        <input
                          type="radio"
                          name="method"
                          value={method.id}
                          checked={selectedMethod === method.id}
                          onChange={() => setSelectedMethod(method.id)}
                          className="mt-1 text-purple-600"
                        />
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">
                            {method.name}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {method.description}
                          </p>
                        </div>
                      </label>
                    ))}
                  </div>
                </>
              )}

              {/* Auto select info */}
              {!selectedMethod && (
                <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex gap-2">
                  <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-blue-700 dark:text-blue-400">
                    Leave unselected to auto-choose best method based on your risk profile
                  </p>
                </div>
              )}
            </div>

            {/* Advanced Settings */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center justify-between w-full text-sm font-medium 
                         text-gray-700 dark:text-gray-300 hover:text-gray-900"
              >
                <span className="flex items-center gap-2">
                  <Settings2 className="w-4 h-4" />
                  Advanced Settings
                </span>
                {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showAdvanced && (
                <div className="mt-4 space-y-4">
                  {/* Position Limits */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">
                        Min Positions
                      </label>
                      <input
                        type="number"
                        min={3}
                        max={maxPositions}
                        value={minPositions}
                        onChange={(e) => setMinPositions(Number(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 
                                 rounded-lg bg-white dark:bg-gray-700 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">
                        Max Positions
                      </label>
                      <input
                        type="number"
                        min={minPositions}
                        max={50}
                        value={maxPositions}
                        onChange={(e) => setMaxPositions(Number(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 
                                 rounded-lg bg-white dark:bg-gray-700 text-sm"
                      />
                    </div>
                  </div>

                  {/* Max Weight */}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      Max Weight per Asset: {(maxWeightPerAsset * 100).toFixed(0)}%
                    </label>
                    <input
                      type="range"
                      min={0.05}
                      max={0.50}
                      step={0.01}
                      value={maxWeightPerAsset}
                      onChange={(e) => setMaxWeightPerAsset(Number(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>5%</span>
                      <span>50%</span>
                    </div>
                  </div>

                  {/* Custom Universe */}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      Custom Universe (comma-separated symbols)
                    </label>
                    <input
                      type="text"
                      value={customUniverse}
                      onChange={(e) => setCustomUniverse(e.target.value)}
                      placeholder="AAPL, MSFT, GOOGL, ..."
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 
                               rounded-lg bg-white dark:bg-gray-700 text-sm"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Leave empty to use default S&P 500 universe
                    </p>
                  </div>

                  {/* Excluded Symbols */}
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">
                      Excluded Symbols (comma-separated)
                    </label>
                    <input
                      type="text"
                      value={excludedSymbols}
                      onChange={(e) => setExcludedSymbols(e.target.value)}
                      placeholder="TSLA, META, ..."
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 
                               rounded-lg bg-white dark:bg-gray-700 text-sm"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 
                        bg-gray-50 dark:bg-gray-800/50 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isOptimizing}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-gray-700 
                       dark:text-gray-300 bg-white dark:bg-gray-700 border 
                       border-gray-300 dark:border-gray-600 rounded-lg 
                       hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isOptimizing}
              className="flex-1 px-4 py-2.5 text-sm font-medium text-white 
                       bg-purple-600 rounded-lg hover:bg-purple-700 
                       disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isOptimizing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white 
                                rounded-full animate-spin" />
                  Optimizing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Run Optimization
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default OptimizationModal;
