/**
 * Markets Page
 */
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Globe } from 'lucide-react';

const Markets = () => {
  return (
    <Layout title="Markets">
      <Card>
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-secondary-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Globe className="w-8 h-8 text-secondary-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Market Overview</h2>
          <p className="text-surface-400">Coming soon... Browse stocks, ETFs, and cryptocurrencies.</p>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Markets;
