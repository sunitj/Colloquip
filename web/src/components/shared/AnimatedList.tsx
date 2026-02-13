import { motion } from 'motion/react';
import { cn } from '@/lib/utils';

interface AnimatedListProps {
  children: React.ReactNode;
  className?: string;
  staggerDelay?: number;
}

interface AnimatedItemProps {
  children: React.ReactNode;
  className?: string;
}

const containerVariants = {
  hidden: {},
  visible: (staggerDelay: number) => ({
    transition: {
      staggerChildren: staggerDelay / 1000,
    },
  }),
};

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: 'easeOut' as const,
    },
  },
};

export function AnimatedList({
  children,
  className,
  staggerDelay = 50,
}: AnimatedListProps) {
  return (
    <motion.div
      className={cn(className)}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      custom={staggerDelay}
    >
      {children}
    </motion.div>
  );
}

export function AnimatedItem({ children, className }: AnimatedItemProps) {
  return (
    <motion.div className={cn(className)} variants={itemVariants}>
      {children}
    </motion.div>
  );
}
