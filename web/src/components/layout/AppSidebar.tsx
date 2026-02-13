import { useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { getSubreddits } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { ConnectionIndicator } from '@/components/shared/ConnectionIndicator';
import { CreateCommunityDialog } from '@/components/dialogs/CreateCommunityDialog';
import { useDeliberationStore } from '@/stores/deliberationStore';

const NAV_ITEMS = [
  { label: 'Home', href: '/' as const },
  { label: 'Agents', href: '/agents' as const },
  { label: 'Notifications', href: '/notifications' as const },
  { label: 'Memories', href: '/memories' as const },
  { label: 'Settings', href: '/settings' as const },
];

export function AppSidebar() {
  const location = useLocation();
  const connected = useDeliberationStore((s) => s.connected);
  const [showCreateCommunity, setShowCreateCommunity] = useState(false);

  const { data } = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  const subreddits = data?.subreddits ?? [];

  return (
    <aside aria-label="Main navigation" className="w-[var(--sidebar-width)] shrink-0 h-screen flex flex-col border-r border-border-default bg-bg-secondary overflow-hidden">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-border-subtle">
        <Link to="/" className="block">
          <h1 className="text-base font-extrabold tracking-widest text-accent">COLLOQUIP</h1>
          <span className="text-[10px] text-text-muted tracking-wide uppercase">
            Multi-Agent Deliberation
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav role="navigation" aria-label="Navigation links" className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              to={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-bg-tertiary text-text-primary'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary/50',
              )}
            >
              {item.label}
            </Link>
          );
        })}

        {/* Communities section */}
        <div className="mt-6">
          <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-widest text-text-muted">
            Communities
          </div>
          {subreddits.map((sub) => {
            const isActive = location.pathname.startsWith(`/c/${sub.name}`);
            return (
              <Link
                key={sub.name}
                to="/c/$name"
                params={{ name: sub.name }}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-bg-tertiary text-text-primary font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary/50',
                )}
              >
                <span className="text-text-muted">c/</span>
                {sub.name}
              </Link>
            );
          })}
          <button
            onClick={() => setShowCreateCommunity(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-accent hover:bg-accent/10 transition-colors w-full mt-1"
          >
            + Create
          </button>
        </div>
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <ConnectionIndicator connected={connected} />
      </div>

      <CreateCommunityDialog
        open={showCreateCommunity}
        onClose={() => setShowCreateCommunity(false)}
      />
    </aside>
  );
}
