import { Button } from '@/components/ui/Button';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
}

function friendlyMessage(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes('platform not initialized') || lower.includes('not initialized')) {
    return 'Initialize the platform in Settings to get started.';
  }
  if (lower.includes('outcome tracking not initialized')) {
    return 'Available after platform initialization.';
  }
  if (lower.includes('503') || lower.includes('service unavailable')) {
    return 'The backend is starting up. Please wait a moment.';
  }
  if (lower.includes('failed to fetch') || lower.includes('network')) {
    return 'Unable to reach the server. Check your connection.';
  }
  return raw;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="flex items-center gap-3 px-5 py-3 bg-pastel-rose-bg border border-pastel-rose/30 rounded-xl text-sm text-[#C95A6B]">
      <span className="flex-1">{friendlyMessage(message)}</span>
      {onRetry && (
        <Button variant="ghost" size="sm" onClick={onRetry} className="text-[#C95A6B] hover:text-[#B04858]">
          Retry
        </Button>
      )}
    </div>
  );
}
