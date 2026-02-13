import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import * as Collapsible from '@radix-ui/react-collapsible';
import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';
import { TRIGGER_COLORS } from '@/lib/agentColors';
import type { TriggerEntry } from '@/types/deliberation';

interface TriggerDrawerProps {
  triggers: TriggerEntry[];
}

export function TriggerDrawer({ triggers }: TriggerDrawerProps) {
  const [open, setOpen] = useState(false);

  if (triggers.length === 0) return null;

  const sortedTriggers = [...triggers].reverse();

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <Collapsible.Trigger
        className={cn(
          'flex items-center gap-2 text-sm font-medium text-text-secondary',
          'transition-colors hover:text-text-primary px-4 py-2 w-full',
        )}
      >
        <ChevronDown
          className={cn(
            'h-4 w-4 transition-transform duration-200',
            open && 'rotate-180',
          )}
        />
        Trigger Log ({triggers.length})
      </Collapsible.Trigger>

      <Collapsible.Content>
        <div className="max-h-[300px] overflow-y-auto px-4 pb-4 space-y-2">
          {sortedTriggers.map((trigger, index) => {
            const color = getAgentColor(trigger.agentId);

            return (
              <div
                key={`${trigger.agentId}-${trigger.postIndex}-${index}`}
                className="flex items-start gap-2 text-xs"
              >
                <span className="shrink-0 text-text-muted">
                  #{trigger.postIndex}
                </span>
                <span
                  className="font-medium shrink-0"
                  style={{ color }}
                >
                  {trigger.agentName}
                </span>
                <div className="flex flex-wrap gap-1">
                  {trigger.rules.map((rule) => (
                    <span
                      key={rule}
                      className="px-1.5 py-0.5 rounded-radius-sm"
                      style={{
                        backgroundColor: `${TRIGGER_COLORS[rule] ?? '#6B7280'}1A`,
                        color: TRIGGER_COLORS[rule] ?? '#6B7280',
                      }}
                    >
                      {rule.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
