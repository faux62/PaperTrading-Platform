/**
 * Main Layout Component
 */
import { clsx } from 'clsx';
import { useUIStore } from '../../store/uiStore';
import Sidebar from './Sidebar';
import Header from './Header';
import { ToastContainer } from '../common';

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
}

const Layout = ({ children, title }: LayoutProps) => {
  const { sidebarCollapsed } = useUIStore();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <Header title={title} />
      
      {/* Main Content */}
      <main
        className={clsx(
          'pt-16 min-h-screen transition-all duration-300',
          sidebarCollapsed ? 'pl-16' : 'pl-64'
        )}
      >
        <div className="p-6">
          {children}
        </div>
      </main>

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
};

export default Layout;
