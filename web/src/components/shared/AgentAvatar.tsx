import { cn } from '@/lib/utils';
import { getAgentColor, getAgentTextColor, getAgentInitials } from '@/lib/agentColors';

interface AgentAvatarProps {
  agentType: string;
  displayName: string;
  isRedTeam?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeStyles = {
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-xs',
  lg: 'w-11 h-11 text-xs',
};

export function AgentAvatar({ agentType, displayName, isRedTeam, size = 'md', className }: AgentAvatarProps) {
  const bgColor = getAgentColor(agentType, isRedTeam);
  const textColor = getAgentTextColor(agentType, isRedTeam);
  const initials = getAgentInitials(displayName);

  return (
    <div
      className={cn(
        'inline-flex items-center justify-center rounded-full font-bold shrink-0',
        sizeStyles[size],
        className,
      )}
      style={{ backgroundColor: `${bgColor}25`, color: textColor }}
      title={displayName}
    >
      {initials}
    </div>
  );
}
