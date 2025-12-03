/**
 * Security Settings Component
 * Password change and security options
 */
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, Button, Input } from '../common';
import { Shield, Key, Clock, AlertTriangle } from 'lucide-react';

interface SecuritySettingsProps {
  onPasswordChange?: (oldPassword: string, newPassword: string) => Promise<void>;
  lastPasswordChange?: Date;
  activeSessions?: number;
}

export const SecuritySettings: React.FC<SecuritySettingsProps> = ({
  onPasswordChange,
  lastPasswordChange,
  activeSessions = 1,
}) => {
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validatePassword = (password: string): string[] => {
    const issues: string[] = [];
    if (password.length < 8) issues.push('At least 8 characters');
    if (!/[A-Z]/.test(password)) issues.push('One uppercase letter');
    if (!/[a-z]/.test(password)) issues.push('One lowercase letter');
    if (!/[0-9]/.test(password)) issues.push('One number');
    if (!/[!@#$%^&*]/.test(password)) issues.push('One special character (!@#$%^&*)');
    return issues;
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onPasswordChange) return;

    setErrors({});
    setMessage(null);

    // Validate
    const newErrors: Record<string, string> = {};
    if (!passwordForm.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }

    const passwordIssues = validatePassword(passwordForm.newPassword);
    if (passwordIssues.length > 0) {
      newErrors.newPassword = `Missing: ${passwordIssues.join(', ')}`;
    }

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    try {
      await onPasswordChange(passwordForm.currentPassword, passwordForm.newPassword);
      setMessage({ type: 'success', text: 'Password changed successfully' });
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to change password. Please check your current password.' });
    } finally {
      setIsLoading(false);
    }
  };

  const getPasswordStrength = (password: string): { strength: number; label: string; color: string } => {
    const issues = validatePassword(password);
    const strength = Math.max(0, 5 - issues.length);
    
    if (strength <= 1) return { strength, label: 'Weak', color: 'bg-danger-500' };
    if (strength <= 2) return { strength, label: 'Fair', color: 'bg-warning-500' };
    if (strength <= 3) return { strength, label: 'Good', color: 'bg-yellow-500' };
    if (strength <= 4) return { strength, label: 'Strong', color: 'bg-success-500' };
    return { strength, label: 'Excellent', color: 'bg-primary-500' };
  };

  const passwordStrength = getPasswordStrength(passwordForm.newPassword);

  return (
    <div className="space-y-6">
      {/* Change Password */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Change Password</h3>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <Input
              type="password"
              label="Current Password"
              value={passwordForm.currentPassword}
              onChange={(e) => setPasswordForm(prev => ({ ...prev, currentPassword: e.target.value }))}
              error={errors.currentPassword}
              placeholder="Enter current password"
            />

            <div>
              <Input
                type="password"
                label="New Password"
                value={passwordForm.newPassword}
                onChange={(e) => setPasswordForm(prev => ({ ...prev, newPassword: e.target.value }))}
                error={errors.newPassword}
                placeholder="Enter new password"
              />
              {passwordForm.newPassword && (
                <div className="mt-2">
                  <div className="flex gap-1 mb-1">
                    {[...Array(5)].map((_, i) => (
                      <div
                        key={i}
                        className={`h-1 flex-1 rounded ${
                          i < passwordStrength.strength ? passwordStrength.color : 'bg-surface-600'
                        }`}
                      />
                    ))}
                  </div>
                  <p className={`text-xs ${
                    passwordStrength.strength < 3 ? 'text-warning-500' : 'text-success-500'
                  }`}>
                    Password strength: {passwordStrength.label}
                  </p>
                </div>
              )}
            </div>

            <Input
              type="password"
              label="Confirm New Password"
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm(prev => ({ ...prev, confirmPassword: e.target.value }))}
              error={errors.confirmPassword}
              placeholder="Confirm new password"
            />

            {message && (
              <div className={`p-3 rounded ${
                message.type === 'success' 
                  ? 'bg-success-500/10 text-success-500' 
                  : 'bg-danger-500/10 text-danger-500'
              }`}>
                {message.text}
              </div>
            )}

            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Changing...' : 'Change Password'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Security Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-500" />
            <h3 className="text-lg font-semibold text-white">Security Status</h3>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-surface-700">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-surface-400" />
                <span className="text-surface-300">Last password change</span>
              </div>
              <span className="text-white">
                {lastPasswordChange 
                  ? lastPasswordChange.toLocaleDateString() 
                  : 'Never'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-surface-700">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-surface-400" />
                <span className="text-surface-300">Active sessions</span>
              </div>
              <span className="text-white">{activeSessions}</span>
            </div>

            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-warning-500" />
                <span className="text-surface-300">Two-factor authentication</span>
              </div>
              <span className="text-warning-500">Not enabled</span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-surface-700 rounded-lg">
            <p className="text-sm text-surface-400">
              Two-factor authentication adds an extra layer of security to your account.
              This feature will be available soon.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SecuritySettings;
