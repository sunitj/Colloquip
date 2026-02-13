import { useState } from 'react';
import { Link, useLocation } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import { getSubreddits } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { ConnectionIndicator } from '@/components/shared/ConnectionIndicator';
import { CreateCommunityDialog } from '@/components/dialogs/CreateCommunityDialog';
import { useDeliberationStore } from '@/stores/deliberationStore';
import { Home, Users, Bell, Lightbulb, Settings, Plus } from 'lucide-react';

const NAV_ITEMS = [
  { label: 'Home', href: '/' as const, icon: Home },
  { label: 'Agents', href: '/agents' as const, icon: Users },
  { label: 'Notifications', href: '/notifications' as const, icon: Bell },
  { label: 'Memories', href: '/memories' as const, icon: Lightbulb },
  { label: 'Settings', href: '/settings' as const, icon: Settings },
];

const COMMUNITY_DOT_COLORS = [
  'bg-pastel-rose',
  'bg-pastel-sky',
  'bg-pastel-mint',
  'bg-pastel-peach',
  'bg-pastel-lemon',
  'bg-pastel-lavender',
  'bg-pastel-lilac',
  'bg-pastel-rose',
];

function getCommunityDotColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i);
    hash |= 0;
  }
  return COMMUNITY_DOT_COLORS[Math.abs(hash) % COMMUNITY_DOT_COLORS.length];
}

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
    <aside aria-label="Main navigation" className="w-[var(--sidebar-width)] shrink-0 h-screen flex flex-col bg-bg-sidebar border-r border-border-default overflow-hidden">
      {/* Brand */}
      <div className="px-6 py-5 border-b border-border-subtle">
        <Link to="/" className="block">
          <h1 className="text-lg font-extrabold tracking-widest bg-gradient-to-r from-pastel-rose via-pastel-lemon via-pastel-mint via-pastel-sky to-pastel-lavender bg-clip-text text-transparent font-[family-name:var(--font-heading)]">COLLOQUIP</h1>
          <span className="text-xs text-text-muted tracking-wide">
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
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              to={item.href}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-accent/10 text-accent'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-secondary/60',
              )}
            >
              <Icon size={18} strokeWidth={isActive ? 2.5 : 2} />
              {item.label}
            </Link>
          );
        })}

        {/* Communities section */}
        <div className="mt-6">
          <div className="px-3 mb-2 text-xs font-semibold text-text-secondary">
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
                  'flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-sm transition-all duration-200',
                  isActive
                    ? 'bg-accent/10 text-accent font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-secondary/60',
                )}
              >
                <span className={cn('w-2 h-2 rounded-full shrink-0', getCommunityDotColor(sub.name))} />
                {sub.name}
              </Link>
            );
          })}
          <button
            onClick={() => setShowCreateCommunity(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm text-accent hover:bg-accent/10 transition-all duration-200 w-full mt-1 border border-dashed border-pastel-lavender/30"
          >
            <Plus size={14} />
            Create
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
