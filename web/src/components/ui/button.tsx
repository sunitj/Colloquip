import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-root disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-white hover:bg-accent-hover shadow-sm",
        secondary:
          "bg-bg-elevated text-text-primary border border-border-default hover:bg-bg-overlay",
        ghost:
          "text-text-secondary hover:bg-bg-elevated hover:text-text-primary",
        outline:
          "border border-border-default bg-transparent text-text-primary hover:bg-bg-elevated hover:border-border-accent",
        destructive:
          "bg-destructive text-white hover:bg-destructive/90 shadow-sm",
      },
      size: {
        sm: "h-8 px-3 text-xs rounded-sm",
        default: "h-10 px-4 py-2",
        lg: "h-12 px-6 text-base rounded-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
