/**
 * Settings Page
 */
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { Settings as SettingsIcon } from 'lucide-react';

const Settings = () => {
  return (
    <Layout title="Settings">
      <Card>
        <CardContent className="p-12 text-center">
          <div className="w-16 h-16 bg-surface-700 rounded-full flex items-center justify-center mx-auto mb-4">
            <SettingsIcon className="w-8 h-8 text-surface-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Account Settings</h2>
          <p className="text-surface-400">Coming soon... Manage your profile, preferences, and security.</p>
        </CardContent>
      </Card>
    </Layout>
  );
};

export default Settings;
