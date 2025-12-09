/**
 * MLInsights Page
 * 
 * Machine Learning insights dashboard page
 */
import React from 'react';
import { Layout } from '../components/layout';
import { MLInsightsPanel } from '../components/ml';

const MLInsights: React.FC = () => {
  return (
    <Layout title="ML Insights">
      <MLInsightsPanel />
    </Layout>
  );
};

export default MLInsights;
