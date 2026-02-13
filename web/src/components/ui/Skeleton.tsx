import { Skeleton as HeroSkeleton } from '@heroui/react';
import { cn } from '@/lib/utils';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <HeroSkeleton
      className={cn('rounded-xl', className)}
      {...props}
    />
  );
}
