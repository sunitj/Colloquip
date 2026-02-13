import { cn } from '@/lib/utils';
import { getAgentColor, getAgentInitials } from '@/lib/agentColors';

interface AgentAvatarProps {
  displayName: string;
  agentType: string;
  isRedTeam?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const sizeMap = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg',
} as const;

export function AgentAvatar({
  displayName,
  agentType,
  isRedTeam = false,
  size = 'md',
  className,
}: AgentAvatarProps) {
  const color = getAgentColor(agentType, isRedTeam);
  const initials = getAgentInitials(displayName);

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-full font-semibold text-white shrink-0',
        sizeMap[size],
        className,
      )}
      style={{ backgroundColor: color }}
      title={displayName}
    >
      {initials}
    </div>
  );
}
