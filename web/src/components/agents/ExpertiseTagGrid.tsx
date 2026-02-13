import { Badge } from '@/components/ui/badge';

interface ExpertiseTagGridProps {
  tags: string[];
  label?: string;
}

export function ExpertiseTagGrid({ tags, label }: ExpertiseTagGridProps) {
  if (!Array.isArray(tags) || tags.length === 0) return null;

  return (
    <div>
      {label && (
        <h4 className="text-sm font-medium text-text-muted uppercase tracking-wider mb-2">
          {label}
        </h4>
      )}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Badge key={tag} variant="secondary">
            {tag}
          </Badge>
        ))}
      </div>
    </div>
  );
}
