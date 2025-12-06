/**
 * Profile Settings Component
 * User profile management
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, Button, Input } from '../common';
import { User, Mail, Lock, Save } from 'lucide-react';

interface ProfileData {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
}

interface ProfileSettingsProps {
  initialData?: Partial<ProfileData>;
  onSave?: (data: ProfileData) => Promise<void>;
}

export const ProfileSettings: React.FC<ProfileSettingsProps> = ({
  initialData = {},
  onSave,
}) => {
  const [formData, setFormData] = useState<ProfileData>({
    username: initialData.username || '',
    email: initialData.email || '',
    firstName: initialData.firstName || '',
    lastName: initialData.lastName || '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onSave) return;

    setIsLoading(true);
    setMessage(null);

    try {
      await onSave(formData);
      setMessage({ type: 'success', text: 'Profile updated successfully' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to update profile' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <User className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-white">Profile Information</h3>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1">
                First Name
              </label>
              <Input
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                placeholder="Enter first name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-1">
                Last Name
              </label>
              <Input
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                placeholder="Enter last name"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">
              Username
            </label>
            <Input
              name="username"
              value={formData.username}
              disabled
              className="bg-surface-700 text-surface-400 cursor-not-allowed"
              placeholder="Username"
            />
            <p className="text-xs text-surface-500 mt-1">Username cannot be changed</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">
              <Mail className="w-4 h-4 inline mr-1" />
              Email
            </label>
            <Input
              type="email"
              name="email"
              value={formData.email}
              disabled
              className="bg-surface-700 text-surface-400 cursor-not-allowed"
              placeholder="Email"
            />
            <p className="text-xs text-surface-500 mt-1">Email cannot be changed</p>
          </div>

          {message && (
            <div className={`p-3 rounded ${
              message.type === 'success' 
                ? 'bg-success-500/10 text-success-500' 
                : 'bg-danger-500/10 text-danger-500'
            }`}>
              {message.text}
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" disabled={isLoading}>
              <Save className="w-4 h-4 mr-2" />
              {isLoading ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

interface PasswordChangeProps {
  onChangePassword?: (currentPassword: string, newPassword: string) => Promise<void>;
}

export const PasswordChange: React.FC<PasswordChangeProps> = ({ onChangePassword }) => {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (formData.newPassword !== formData.confirmPassword) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    if (formData.newPassword.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
      return;
    }

    if (!onChangePassword) return;

    setIsLoading(true);
    setMessage(null);

    try {
      await onChangePassword(formData.currentPassword, formData.newPassword);
      setMessage({ type: 'success', text: 'Password changed successfully' });
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to change password' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lock className="w-5 h-5 text-primary-500" />
          <h3 className="text-lg font-semibold text-white">Change Password</h3>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">
              Current Password
            </label>
            <Input
              type="password"
              name="currentPassword"
              value={formData.currentPassword}
              onChange={handleChange}
              placeholder="Enter current password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">
              New Password
            </label>
            <Input
              type="password"
              name="newPassword"
              value={formData.newPassword}
              onChange={handleChange}
              placeholder="Enter new password"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-surface-300 mb-1">
              Confirm New Password
            </label>
            <Input
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm new password"
            />
          </div>

          {message && (
            <div className={`p-3 rounded ${
              message.type === 'success' 
                ? 'bg-success-500/10 text-success-500' 
                : 'bg-danger-500/10 text-danger-500'
            }`}>
              {message.text}
            </div>
          )}

          <div className="flex justify-end">
            <Button type="submit" disabled={isLoading}>
              <Lock className="w-4 h-4 mr-2" />
              {isLoading ? 'Changing...' : 'Change Password'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default ProfileSettings;
