import { Button as HeroButton } from '@heroui/react';
import type { PressEvent } from '@heroui/react';
import { cn } from '@/lib/utils';

type ButtonVariant = 'default' | 'ghost' | 'outline' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  disabled?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  type?: 'button' | 'submit' | 'reset';
  children?: React.ReactNode;
  'aria-label'?: string;
}

const variantMap = {
  default: 'primary',
  ghost: 'ghost',
  outline: 'outline',
  destructive: 'danger',
} as const;

const sizeMap: Record<ButtonSize, 'sm' | 'md' | 'lg'> = {
  sm: 'sm',
  md: 'md',
  lg: 'lg',
  icon: 'md',
};

export function Button({
  className,
  variant = 'default',
  size = 'md',
  disabled,
  onClick,
  type,
  children,
  'aria-label': ariaLabel,
}: ButtonProps) {
  return (
    <HeroButton
      variant={variantMap[variant]}
      size={sizeMap[size]}
      isDisabled={disabled}
      isIconOnly={size === 'icon'}
      type={type}
      aria-label={ariaLabel}
      className={cn(
        'rounded-xl font-medium font-[family-name:var(--font-heading)]',
        size === 'icon' && 'h-11 w-11',
        className,
      )}
      onPress={onClick as unknown as (e: PressEvent) => void}
    >
      {children}
    </HeroButton>
  );
}
