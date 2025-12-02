/**
 * Portfolio Page
 */
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Briefcase } from 'lucide-react';

const Portfolio = () => {
  return (
    <Layout title="Portfolio">
      <Card>
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-primary-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Briefcase className="w-8 h-8 text-primary-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Portfolio Management</h2>
          <p className="text-surface-400">Coming soon... Track your holdings, performance, and allocation.</p>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Portfolio;
