import { motion } from 'motion/react';

interface ThinkingIndicatorProps {
  message?: string;
}

export function ThinkingIndicator({
  message = 'Agents deliberating...',
}: ThinkingIndicatorProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-bg-elevated p-4">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="inline-block h-2 w-2 rounded-full bg-text-accent"
            animate={{ y: [0, -6, 0] }}
            transition={{
              duration: 0.6,
              repeat: Infinity,
              delay: i * 0.15,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
      <span className="text-sm text-text-secondary">{message}</span>
    </div>
  );
}
