/**
 * Admin Page - User Management
 * Superuser only - manage users, enable/disable, delete
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Layout } from '../components/layout';
import { Card, CardContent, CardHeader, Button, Input, Badge } from '../components/common';
import { 
  Users, Shield, UserX, UserCheck, Trash2, Search, 
  RefreshCw, AlertTriangle, ChevronLeft, ChevronRight,
  BarChart3, Activity
} from 'lucide-react';
import { adminApi } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Navigate } from 'react-router-dom';

interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  base_currency: string;
  created_at: string;
  last_login: string | null;
  portfolio_count: number;
}

interface AdminStats {
  total_users: number;
  active_users: number;
  disabled_users: number;
  superusers: number;
  total_portfolios: number;
  users_today: number;
  users_this_week: number;
}

interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

const Admin: React.FC = () => {
  const currentUser = useAuthStore(state => state.user);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  
  // Modal states
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [disableReason, setDisableReason] = useState('');

  // Check if user is admin
  if (!currentUser?.is_superuser) {
    return <Navigate to="/dashboard" replace />;
  }

  const loadStats = useCallback(async () => {
    try {
      const data = await adminApi.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data: UserListResponse = await adminApi.listUsers({
        page,
        page_size: 15,
        search: search || undefined,
        is_active: filterActive,
      });
      setUsers(data.users);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [page, search, filterActive]);

  useEffect(() => {
    loadStats();
    loadUsers();
  }, [loadStats, loadUsers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadUsers();
  };

  const handleEnableUser = async (user: User) => {
    setActionLoading(user.id);
    try {
      await adminApi.updateUserStatus(user.id, true);
      await loadUsers();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enable user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDisableUser = async () => {
    if (!selectedUser) return;
    setActionLoading(selectedUser.id);
    try {
      await adminApi.updateUserStatus(selectedUser.id, false, disableReason || undefined);
      setShowDisableModal(false);
      setSelectedUser(null);
      setDisableReason('');
      await loadUsers();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disable user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    setActionLoading(selectedUser.id);
    try {
      await adminApi.deleteUser(selectedUser.id);
      setShowDeleteModal(false);
      setSelectedUser(null);
      await loadUsers();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user');
    } finally {
      setActionLoading(null);
    }
  };

  const openDisableModal = (user: User) => {
    setSelectedUser(user);
    setDisableReason('');
    setShowDisableModal(true);
  };

  const openDeleteModal = (user: User) => {
    setSelectedUser(user);
    setShowDeleteModal(true);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Layout>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Shield className="w-7 h-7 text-primary-500" />
              Admin Panel
            </h1>
            <p className="text-surface-400 mt-1">Manage users and platform settings</p>
          </div>
          <Button
            onClick={() => { loadStats(); loadUsers(); }}
            variant="secondary"
            className="flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <Users className="w-6 h-6 text-primary-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-white">{stats.total_users}</p>
                <p className="text-xs text-surface-400">Total Users</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <UserCheck className="w-6 h-6 text-green-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-green-400">{stats.active_users}</p>
                <p className="text-xs text-surface-400">Active</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <UserX className="w-6 h-6 text-red-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-red-400">{stats.disabled_users}</p>
                <p className="text-xs text-surface-400">Disabled</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <Shield className="w-6 h-6 text-yellow-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-yellow-400">{stats.superusers}</p>
                <p className="text-xs text-surface-400">Admins</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <BarChart3 className="w-6 h-6 text-blue-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-blue-400">{stats.total_portfolios}</p>
                <p className="text-xs text-surface-400">Portfolios</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <Activity className="w-6 h-6 text-purple-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-purple-400">{stats.users_today}</p>
                <p className="text-xs text-surface-400">Today</p>
              </CardContent>
            </Card>
            <Card className="bg-surface-800/50">
              <CardContent className="p-4 text-center">
                <Activity className="w-6 h-6 text-cyan-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-cyan-400">{stats.users_this_week}</p>
                <p className="text-xs text-surface-400">This Week</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">×</button>
          </div>
        )}

        {/* Users Table */}
        <Card>
          <CardHeader>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Users className="w-5 h-5" />
                User Management ({total})
              </h2>
              
              <div className="flex flex-col md:flex-row gap-3">
                {/* Search */}
                <form onSubmit={handleSearch} className="flex gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                    <Input
                      type="text"
                      placeholder="Search users..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="pl-9 w-48"
                    />
                  </div>
                  <Button type="submit" variant="secondary">Search</Button>
                </form>
                
                {/* Filter */}
                <select
                  value={filterActive === undefined ? 'all' : filterActive ? 'active' : 'disabled'}
                  onChange={(e) => {
                    const val = e.target.value;
                    setFilterActive(val === 'all' ? undefined : val === 'active');
                    setPage(1);
                  }}
                  className="bg-surface-700 border border-surface-600 rounded-lg px-3 py-2 text-white text-sm"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active Only</option>
                  <option value="disabled">Disabled Only</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 text-primary-500 animate-spin" />
              </div>
            ) : users.length === 0 ? (
              <div className="text-center py-12 text-surface-400">
                No users found
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-sm text-surface-400 border-b border-surface-700">
                        <th className="pb-3 font-medium">User</th>
                        <th className="pb-3 font-medium">Email</th>
                        <th className="pb-3 font-medium text-center">Status</th>
                        <th className="pb-3 font-medium text-center">Role</th>
                        <th className="pb-3 font-medium text-center">Portfolios</th>
                        <th className="pb-3 font-medium">Created</th>
                        <th className="pb-3 font-medium">Last Login</th>
                        <th className="pb-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-700">
                      {users.map((user) => (
                        <tr key={user.id} className="text-sm hover:bg-surface-800/50">
                          <td className="py-3">
                            <div>
                              <p className="font-medium text-white">{user.username}</p>
                              {user.full_name && (
                                <p className="text-xs text-surface-400">{user.full_name}</p>
                              )}
                            </div>
                          </td>
                          <td className="py-3 text-surface-300">{user.email}</td>
                          <td className="py-3 text-center">
                            <Badge variant={user.is_active ? 'success' : 'danger'}>
                              {user.is_active ? 'Active' : 'Disabled'}
                            </Badge>
                          </td>
                          <td className="py-3 text-center">
                            {user.is_superuser ? (
                              <Badge variant="warning">Admin</Badge>
                            ) : (
                              <span className="text-surface-400">User</span>
                            )}
                          </td>
                          <td className="py-3 text-center text-surface-300">
                            {user.portfolio_count}
                          </td>
                          <td className="py-3 text-surface-400 text-xs">
                            {formatDate(user.created_at)}
                          </td>
                          <td className="py-3 text-surface-400 text-xs">
                            {formatDate(user.last_login)}
                          </td>
                          <td className="py-3">
                            <div className="flex items-center justify-end gap-2">
                              {/* Cannot modify self or other admins */}
                              {user.id !== currentUser?.id && !user.is_superuser && (
                                <>
                                  {user.is_active ? (
                                    <button
                                      onClick={() => openDisableModal(user)}
                                      disabled={actionLoading === user.id}
                                      className="p-1.5 text-yellow-400 hover:bg-yellow-500/10 rounded transition-colors"
                                      title="Disable user"
                                    >
                                      <UserX className="w-4 h-4" />
                                    </button>
                                  ) : (
                                    <button
                                      onClick={() => handleEnableUser(user)}
                                      disabled={actionLoading === user.id}
                                      className="p-1.5 text-green-400 hover:bg-green-500/10 rounded transition-colors"
                                      title="Enable user"
                                    >
                                      <UserCheck className="w-4 h-4" />
                                    </button>
                                  )}
                                  <button
                                    onClick={() => openDeleteModal(user)}
                                    disabled={actionLoading === user.id}
                                    className="p-1.5 text-red-400 hover:bg-red-500/10 rounded transition-colors"
                                    title="Delete user"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                              {(user.id === currentUser?.id || user.is_superuser) && (
                                <span className="text-xs text-surface-500 px-2">
                                  {user.id === currentUser?.id ? '(You)' : '(Admin)'}
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-surface-700">
                    <p className="text-sm text-surface-400">
                      Page {page} of {totalPages}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Disable Modal */}
        {showDisableModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-surface-800 rounded-xl p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <UserX className="w-5 h-5 text-yellow-500" />
                Disable User
              </h3>
              <p className="text-surface-300 mb-4">
                Are you sure you want to disable <strong>{selectedUser.username}</strong>?
                They will no longer be able to log in.
              </p>
              <div className="mb-4">
                <label className="block text-sm text-surface-400 mb-2">
                  Reason (optional - will be included in email)
                </label>
                <textarea
                  value={disableReason}
                  onChange={(e) => setDisableReason(e.target.value)}
                  className="w-full bg-surface-700 border border-surface-600 rounded-lg p-3 text-white text-sm"
                  rows={3}
                  placeholder="e.g., Violation of terms of service..."
                />
              </div>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="secondary"
                  onClick={() => setShowDisableModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDisableUser}
                  disabled={actionLoading === selectedUser.id}
                >
                  {actionLoading === selectedUser.id ? 'Disabling...' : 'Disable User'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Modal */}
        {showDeleteModal && selectedUser && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-surface-800 rounded-xl p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-red-500" />
                Delete User
              </h3>
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4">
                <p className="text-red-400 text-sm">
                  <strong>⚠️ Warning:</strong> This action is irreversible!
                </p>
              </div>
              <p className="text-surface-300 mb-4">
                Are you sure you want to permanently delete <strong>{selectedUser.username}</strong>?
              </p>
              <p className="text-surface-400 text-sm mb-4">
                All their data will be deleted including:
              </p>
              <ul className="text-surface-400 text-sm list-disc list-inside mb-4">
                <li>Portfolios ({selectedUser.portfolio_count})</li>
                <li>Positions and trades</li>
                <li>Watchlists and alerts</li>
                <li>Settings and preferences</li>
              </ul>
              <div className="flex gap-3 justify-end">
                <Button
                  variant="secondary"
                  onClick={() => setShowDeleteModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleDeleteUser}
                  disabled={actionLoading === selectedUser.id}
                >
                  {actionLoading === selectedUser.id ? 'Deleting...' : 'Delete Permanently'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Admin;
