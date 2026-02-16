import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-root",
  {
    variants: {
      variant: {
        default: "bg-accent/15 text-text-accent border border-accent/20",
        secondary:
          "bg-bg-elevated text-text-secondary border border-border-default",
        outline:
          "border border-border-default text-text-primary bg-transparent",
        destructive:
          "bg-destructive/15 text-destructive border border-destructive/20",
        success:
          "bg-success/15 text-success border border-success/20",
        warning:
          "bg-warning/15 text-warning border border-warning/20",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant, className }))}
        {...props}
      />
    );
  }
);
Badge.displayName = "Badge";

export { Badge, badgeVariants };
