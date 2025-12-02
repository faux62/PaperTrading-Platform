/**
 * Header Component
 */
import { clsx } from 'clsx';
import { Bell, Search, Sun, Moon, User } from 'lucide-react';
import { useUIStore } from '../../store/uiStore';
import { useAuthStore } from '../../store/authStore';

interface HeaderProps {
  title?: string;
}

const Header = ({ title }: HeaderProps) => {
  const { theme, toggleTheme, sidebarCollapsed } = useUIStore();
  const { user } = useAuthStore();

  return (
    <header
      className={clsx(
        'fixed top-0 right-0 h-16 bg-surface-900/80 backdrop-blur-md',
        'border-b border-surface-700 z-30',
        'flex items-center justify-between px-6',
        'transition-all duration-300',
        sidebarCollapsed ? 'left-16' : 'left-64'
      )}
    >
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {title && (
          <h1 className="text-xl font-semibold text-white">{title}</h1>
        )}
      </div>

      {/* Search */}
      <div className="flex-1 max-w-xl mx-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
          <input
            type="text"
            placeholder="Search symbols, markets..."
            className={clsx(
              'w-full pl-10 pr-4 py-2 rounded-lg',
              'bg-surface-800 border border-surface-700',
              'text-white placeholder-surface-400',
              'focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500',
              'transition-colors'
            )}
          />
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={clsx(
            'p-2 rounded-lg',
            'text-surface-400 hover:text-white hover:bg-surface-800',
            'transition-colors'
          )}
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>

        {/* Notifications */}
        <button
          className={clsx(
            'p-2 rounded-lg relative',
            'text-surface-400 hover:text-white hover:bg-surface-800',
            'transition-colors'
          )}
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full" />
        </button>

        {/* User Menu */}
        <div className="flex items-center gap-3 ml-2 pl-4 border-l border-surface-700">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-white">{user?.username}</p>
            <p className="text-xs text-surface-400">{user?.email}</p>
          </div>
          <button
            className={clsx(
              'w-10 h-10 rounded-full',
              'bg-primary-500/20 text-primary-400',
              'flex items-center justify-center',
              'hover:bg-primary-500/30 transition-colors'
            )}
          >
            <User className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
