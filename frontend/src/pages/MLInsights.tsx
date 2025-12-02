/**
 * MLInsights Page
 * 
 * Machine Learning insights dashboard page
 */
import React from 'react';
import { MLInsightsPanel } from '../components/ml';

const MLInsights: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-6">
      <MLInsightsPanel />
    </div>
  );
};

export default MLInsights;
