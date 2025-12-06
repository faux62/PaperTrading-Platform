/**
 * Settings Page
 * Complete settings management with tabs for Profile, Preferences, Security, and Data Providers
 */
import React, { useState, useEffect } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent } from '../components/common';
import { User, Settings2, Shield, Database } from 'lucide-react';
import {
  ProfileSettings,
  PreferencesSettings,
  SecuritySettings,
  DataProviderSettings,
} from '../components/settings';
import { authApi } from '../services/api';

type SettingsTab = 'profile' | 'preferences' | 'security' | 'providers';

interface TabConfig {
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
}

interface UserProfile {
  username: string;
  email: string;
  full_name: string | null;
  base_currency: string;
  updated_at: string | null;
}

const tabs: TabConfig[] = [
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'preferences', label: 'Preferences', icon: <Settings2 className="w-4 h-4" /> },
  { id: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
  { id: 'providers', label: 'Data Providers', icon: <Database className="w-4 h-4" /> },
];

const Settings = () => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch user profile on mount
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await authApi.getMe();
        setUserProfile(data);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  // Real API handler for profile save
  const handleProfileSave = async (data: { username: string; email: string; firstName: string; lastName: string }) => {
    const fullName = `${data.firstName} ${data.lastName}`.trim();
    const updated = await authApi.updateMe({ full_name: fullName || undefined });
    setUserProfile(updated);
  };

  const handlePreferencesSave = async (data: unknown) => {
    console.log('Saving preferences:', data);
    // TODO: Implement preferences API when backend supports it
    await new Promise(resolve => setTimeout(resolve, 500));
  };

  // Real API handler for password change
  const handlePasswordChange = async (oldPassword: string, newPassword: string) => {
    await authApi.changePassword(oldPassword, newPassword);
  };

  const handleProviderSave = async (provider: string, apiKey: string) => {
    console.log('Saving provider:', provider, apiKey.slice(0, 4) + '***');
    // TODO: Implement provider API when backend supports it
    await new Promise(resolve => setTimeout(resolve, 500));
  };

  const handleTestConnection = async (provider: string): Promise<boolean> => {
    console.log('Testing connection:', provider);
    await new Promise(resolve => setTimeout(resolve, 1500));
    return Math.random() > 0.3; // Mock success/failure
  };

  // Parse full_name into firstName and lastName
  const parseFullName = (fullName: string | null): { firstName: string; lastName: string } => {
    if (!fullName) return { firstName: '', lastName: '' };
    const parts = fullName.trim().split(' ');
    if (parts.length === 1) return { firstName: parts[0], lastName: '' };
    return { firstName: parts[0], lastName: parts.slice(1).join(' ') };
  };

  const renderTabContent = () => {
    if (loading) {
      return (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
            <p className="text-surface-400 mt-4">Loading...</p>
          </CardContent>
        </Card>
      );
    }

    const { firstName, lastName } = parseFullName(userProfile?.full_name || null);

    switch (activeTab) {
      case 'profile':
        return (
          <ProfileSettings
            initialData={{ 
              username: userProfile?.username || '', 
              email: userProfile?.email || '', 
              firstName, 
              lastName 
            }}
            onSave={handleProfileSave}
          />
        );
      case 'preferences':
        return <PreferencesSettings onSave={handlePreferencesSave} />;
      case 'security':
        return (
          <SecuritySettings
            onPasswordChange={handlePasswordChange}
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
