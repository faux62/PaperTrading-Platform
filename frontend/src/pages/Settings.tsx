/**
 * Settings Page
 * Complete settings management with tabs for Profile, Preferences, Security, and Data Providers
 */
import React, { useState } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { User, Settings2, Shield, Database } from 'lucide-react';
import {
  ProfileSettings,
  PreferencesSettings,
  SecuritySettings,
  DataProviderSettings,
} from '../components/settings';

type SettingsTab = 'profile' | 'preferences' | 'security' | 'providers';

interface TabConfig {
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
}

const tabs: TabConfig[] = [
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'preferences', label: 'Preferences', icon: <Settings2 className="w-4 h-4" /> },
  { id: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
  { id: 'providers', label: 'Data Providers', icon: <Database className="w-4 h-4" /> },
];

const Settings = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');

  // Mock handlers - in production these would call API
  const handleProfileSave = async (data: { username: string; email: string; firstName: string; lastName: string }) => {
    console.log('Saving profile:', data);
    await new Promise(resolve => setTimeout(resolve, 1000));
  };

  const handlePreferencesSave = async (data: unknown) => {
    console.log('Saving preferences:', data);
    await new Promise(resolve => setTimeout(resolve, 1000));
  };

  const handlePasswordChange = async (_oldPassword: string, _newPassword: string) => {
    console.log('Changing password');
    await new Promise(resolve => setTimeout(resolve, 1000));
  };

  const handleProviderSave = async (provider: string, apiKey: string) => {
    console.log('Saving provider:', provider, apiKey.slice(0, 4) + '***');
    await new Promise(resolve => setTimeout(resolve, 1000));
  };

  const handleTestConnection = async (provider: string): Promise<boolean> => {
    console.log('Testing connection:', provider);
    await new Promise(resolve => setTimeout(resolve, 1500));
    return Math.random() > 0.3; // Mock success/failure
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile':
        return (
          <ProfileSettings
            initialData={{ username: 'papertrader', email: 'user@example.com', firstName: 'Paper', lastName: 'Trader' }}
            onSave={handleProfileSave}
          />
        );
      case 'preferences':
        return <PreferencesSettings onSave={handlePreferencesSave} />;
      case 'security':
        return (
          <SecuritySettings
            onPasswordChange={handlePasswordChange}
            lastPasswordChange={new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)}
            activeSessions={2}
          />
        );
      case 'providers':
        return (
          <DataProviderSettings
            onSaveProvider={handleProviderSave}
            onTestConnection={handleTestConnection}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Layout title="Settings">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Navigation */}
        <Card className="lg:w-64 flex-shrink-0">
          <CardContent className="p-2">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                    activeTab === tab.id
                      ? 'bg-primary-500/20 text-primary-400'
                      : 'text-surface-300 hover:bg-surface-700 hover:text-white'
                  }`}
                >
                  {tab.icon}
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {/* Content Area */}
        <div className="flex-1 min-w-0">
          {renderTabContent()}
        </div>
      </div>
    </Layout>
  );
};

export default Settings;
