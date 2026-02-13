import { useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebarStore';
import { useIsMobile } from '@/hooks/useMediaQuery';
import { AppSidebar } from './AppSidebar';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const isMobile = useIsMobile();
  const { isOpen, isCollapsed, setOpen } = useSidebarStore();

  // Close mobile overlay when switching to desktop
  useEffect(() => {
    if (!isMobile) {
      setOpen(true);
    }
  }, [isMobile, setOpen]);

  return (
    <div className="flex h-screen w-full bg-bg-root">
      {/* Desktop sidebar */}
      {!isMobile && (
        <aside
          className={cn(
            'shrink-0 transition-[width] duration-200 ease-in-out',
            isCollapsed ? 'w-16' : 'w-[var(--sidebar-width)]'
          )}
        >
          <AppSidebar />
        </aside>
      )}

      {/* Mobile sidebar overlay */}
      {isMobile && (
        <AnimatePresence>
          {isOpen && (
            <>
              <motion.div
                className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setOpen(false)}
              />
              <motion.aside
                className="fixed inset-y-0 left-0 z-50 w-[var(--sidebar-width)]"
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              >
                <AppSidebar />
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      )}

      {/* Main content */}
      <main className="flex-1 overflow-y-auto min-h-screen">
        {children}
      </main>
    </div>
  );
}
