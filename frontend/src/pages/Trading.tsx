/**
 * Trading Page
 */
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { TrendingUp } from 'lucide-react';

const Trading = () => {
  return (
    <Layout title="Trading">
      <Card>
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-success-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <TrendingUp className="w-8 h-8 text-success-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Trading Terminal</h2>
          <p className="text-surface-400">Coming soon... Execute trades with real-time market data.</p>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Trading;
