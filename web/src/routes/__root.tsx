import { useEffect } from 'react';
import { createRootRoute, Outlet } from '@tanstack/react-router';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { useSidebarStore } from '@/stores/sidebarStore';
import { cn } from '@/lib/utils';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  const { isOpen, setOpen } = useSidebarStore();

  // Auto-close sidebar on mobile navigation
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 768px)');
    const handler = (e: MediaQueryListEvent) => {
      if (e.matches) setOpen(false);
    };
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [setOpen]);

  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:bg-accent focus:text-white focus:px-4 focus:py-2 focus:rounded-xl focus:text-sm"
      >
        Skip to main content
      </a>

      <div className="flex h-screen overflow-hidden bg-bg-primary">
        {/* Mobile backdrop */}
        {isOpen && (
          <div
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm md:hidden"
            onClick={() => setOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar */}
        <div
          className={cn(
            'fixed inset-y-0 left-0 z-50 md:relative md:z-auto transition-transform duration-200',
            isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
          )}
        >
          <AppSidebar />
        </div>

        {/* Main */}
        <main id="main-content" role="main" className="flex-1 overflow-y-auto relative">
          {/* Mobile menu button */}
          <button
            onClick={() => setOpen(!isOpen)}
            className="md:hidden fixed top-3 left-3 z-30 p-2 rounded-xl bg-bg-secondary shadow-md text-text-secondary hover:text-text-primary transition-colors"
            aria-label={isOpen ? 'Close menu' : 'Open menu'}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </button>
          <Outlet />
        </main>
      </div>
    </>
  );
}
