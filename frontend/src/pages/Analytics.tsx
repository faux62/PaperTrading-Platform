/**
 * Analytics Page
 */
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { BarChart3 } from 'lucide-react';

const Analytics = () => {
  return (
    <Layout title="Analytics">
      <Card>
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-warning-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-8 h-8 text-warning-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Portfolio Analytics</h2>
          <p className="text-surface-400">Coming soon... Analyze performance, risk metrics, and trading patterns.</p>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Analytics;
