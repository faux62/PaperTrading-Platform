/**
 * Sidebar Component
 */
import { NavLink, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard,
  TrendingUp,
  Briefcase,
  BarChart3,
  Brain,
  Settings,
  Shield,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { useAuthStore } from '../../store/authStore';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Trading', path: '/trading', icon: TrendingUp },
  { name: 'Portfolio', path: '/portfolio', icon: Briefcase },
  { name: 'Markets', path: '/markets', icon: BarChart3 },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'ML Insights', path: '/ml-insights', icon: Brain },
  { name: 'Settings', path: '/settings', icon: Settings },
  { name: 'Admin', path: '/admin', icon: Shield, adminOnly: true },
];

const Sidebar = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { logout, user } = useAuthStore();
  const location = useLocation();

  // Filter nav items based on user role
  const visibleNavItems = navItems.filter(item => {
    if (item.adminOnly && !user?.is_superuser) return false;
    return true;
  });

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-full bg-surface-900 border-r border-surface-700',
        'flex flex-col transition-all duration-300 z-40',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-surface-700">
        {!sidebarCollapsed && (
          <span className="text-xl font-bold text-white">
            Paper<span className="text-primary-400">Trading</span>
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-surface-800 text-surface-400 hover:text-white transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all',
                    'hover:bg-surface-800',
                    isActive
                      ? 'bg-primary-500/10 text-primary-400 border-l-2 border-primary-400'
                      : 'text-surface-400 hover:text-white'
                  )}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && (
                    <span className="text-sm font-medium">{item.name}</span>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Logout */}
      <div className="p-2 border-t border-surface-700">
        <button
          onClick={() => logout()}
          className={clsx(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg w-full',
            'text-surface-400 hover:text-danger-400 hover:bg-danger-500/10 transition-colors'
          )}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!sidebarCollapsed && (
            <span className="text-sm font-medium">Logout</span>
          )}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
