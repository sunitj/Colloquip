import { createRootRoute, Outlet } from '@tanstack/react-router';
import { Menu } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useIsMobile } from '@/hooks/useMediaQuery';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  const isMobile = useIsMobile();
  const { setOpen } = useSidebarStore();

  return (
    <>
      {/* Skip to content - accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:bg-accent focus:text-white focus:rounded-radius-md"
      >
        Skip to content
      </a>

      <AppShell>
        {/* Mobile hamburger */}
        {isMobile && (
          <div className="sticky top-0 z-30 flex items-center h-14 px-4 bg-bg-root/80 backdrop-blur-md border-b border-border-subtle">
            <button
              onClick={() => setOpen(true)}
              className="flex items-center justify-center h-9 w-9 rounded-radius-md text-text-secondary hover:text-text-primary hover:bg-bg-elevated/30 transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="ml-3 font-semibold tracking-tight text-text-primary">
              COLLOQUIP
            </span>
          </div>
        )}

        <div id="main-content" className="p-6">
          <Outlet />
        </div>
      </AppShell>
    </>
  );
}
