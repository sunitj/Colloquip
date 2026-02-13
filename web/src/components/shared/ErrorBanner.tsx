import { Button } from '@/components/ui/Button';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-error/10 border border-error/20 rounded-md text-sm text-error">
      <span className="flex-1">{message}</span>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="text-error hover:text-error">
          Retry
        </Button>
      )}
    </div>
  );
}
