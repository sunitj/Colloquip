import { cn } from '@/lib/utils';
import { getAgentColor, getAgentBgColor, getAgentInitials } from '@/lib/agentColors';

interface AgentAvatarProps {
  agentType: string;
  displayName: string;
  isRedTeam?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'w-6 h-6 text-[9px]',
  md: 'w-8 h-8 text-[11px]',
  lg: 'w-10 h-10 text-xs',
};

export function AgentAvatar({ agentType, displayName, isRedTeam, size = 'md', className }: AgentAvatarProps) {
  const color = getAgentColor(agentType, isRedTeam);
  const bgColor = getAgentBgColor(color);
  const initials = getAgentInitials(displayName);

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-full font-bold shrink-0',
        sizeStyles[size],
        className,
      )}
      style={{ backgroundColor: bgColor, color, border: `1px solid ${color}40` }}
      title={displayName}
    >
      {initials}
    </div>
  );
}
