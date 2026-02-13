import { useState } from 'react';
import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Home, Users, Brain, Bell, Settings, Plus, Wifi } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebarStore } from '@/stores/sidebarStore';
import { getSubreddits } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { getAgentColor } from '@/lib/agentColors';
import { CreateCommunityDialog } from '@/components/dialogs/CreateCommunityDialog';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/agents', label: 'Agents', icon: Users },
  { to: '/memories', label: 'Memories', icon: Brain },
  { to: '/notifications', label: 'Notifications', icon: Bell },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

export function AppSidebar() {
  const { isCollapsed } = useSidebarStore();
  const [createCommunityOpen, setCreateCommunityOpen] = useState(false);

  const { data } = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  const communities = data?.subreddits ?? [];

  return (
    <div
      className={cn(
        'flex h-full flex-col bg-bg-sidebar border-r border-border-default',
        isCollapsed ? 'w-16' : 'w-[var(--sidebar-width)]'
      )}
    >
      {/* Brand */}
      <div className={cn('flex items-center h-14 shrink-0 border-b border-border-subtle', isCollapsed ? 'justify-center px-2' : 'px-5')}>
        <Link
          to="/"
          className="group font-semibold tracking-tight text-lg text-text-primary transition-colors"
        >
          {isCollapsed ? (
            <span className="group-hover:bg-gradient-to-r group-hover:from-accent group-hover:to-accent-hover group-hover:bg-clip-text group-hover:text-transparent transition-all">
              C
            </span>
          ) : (
            <span className="group-hover:bg-gradient-to-r group-hover:from-accent group-hover:to-accent-hover group-hover:bg-clip-text group-hover:text-transparent transition-all">
              COLLOQUIP
            </span>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 px-2 py-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="group flex items-center gap-3 rounded-md transition-colors"
            activeProps={{
              className:
                'border-l-2 border-text-accent bg-bg-elevated/50 text-text-primary',
            }}
            inactiveProps={{
              className:
                'border-l-2 border-transparent text-text-secondary hover:bg-bg-elevated/30 hover:text-text-primary',
            }}
          >
            {({ isActive }) => (
              <div
                className={cn(
                  'flex items-center gap-3 w-full',
                  isCollapsed ? 'justify-center px-2 py-2.5' : 'px-3 py-2.5'
                )}
              >
                <Icon
                  className={cn(
                    'h-[18px] w-[18px] shrink-0',
                    isActive ? 'text-text-accent' : 'text-text-secondary group-hover:text-text-primary'
                  )}
                />
                {!isCollapsed && (
                  <span className="text-sm font-medium truncate">{label}</span>
                )}
              </div>
            )}
          </Link>
        ))}
      </nav>

      {/* Divider */}
      <div className="mx-4 border-t border-border-subtle" />

      {/* Communities */}
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {!isCollapsed && (
          <p className="px-3 mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">
            Communities
          </p>
        )}

        <div className="flex flex-col gap-0.5">
          {communities.map((community) => {
            const dotColor = getAgentColor(community.name);
            return (
              <Link
                key={community.name}
                to="/c/$name"
                params={{ name: community.name }}
                className="group flex items-center gap-3 rounded-md transition-colors"
                activeProps={{
                  className: 'bg-bg-elevated/50 text-text-primary',
                }}
                inactiveProps={{
                  className:
                    'text-text-secondary hover:bg-bg-elevated/30 hover:text-text-primary',
                }}
              >
                <div
                  className={cn(
                    'flex items-center gap-3 w-full',
                    isCollapsed ? 'justify-center px-2 py-2' : 'px-3 py-2'
                  )}
                >
                  <span
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: dotColor }}
                  />
                  {!isCollapsed && (
                    <span className="text-sm truncate">
                      {community.display_name || community.name}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>

        {/* Create community button */}
        {!isCollapsed && (
          <button
            className="flex items-center gap-2 w-full px-3 py-2 mt-2 text-sm text-text-muted rounded-md transition-colors hover:text-text-secondary hover:border-dashed hover:border hover:border-border-default"
            onClick={() => setCreateCommunityOpen(true)}
          >
            <Plus className="h-4 w-4" />
            <span>Create Community</span>
          </button>
        )}
        {isCollapsed && (
          <button
            className="flex items-center justify-center w-full px-2 py-2 mt-2 text-text-muted rounded-md transition-colors hover:text-text-secondary hover:bg-bg-elevated/30"
            onClick={() => setCreateCommunityOpen(true)}
          >
            <Plus className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Footer - connection indicator */}
      <div
        className={cn(
          'shrink-0 border-t border-border-subtle py-3',
          isCollapsed ? 'px-2 flex justify-center' : 'px-4'
        )}
      >
        <div className="flex items-center gap-2 text-text-muted">
          <Wifi className="h-3.5 w-3.5" />
          {!isCollapsed && (
            <span className="text-xs">Connected</span>
          )}
        </div>
      </div>

      <CreateCommunityDialog
        open={createCommunityOpen}
        onOpenChange={setCreateCommunityOpen}
      />
    </div>
  );
}
