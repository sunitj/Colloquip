interface PostClaimsBlockProps {
  claims: string[];
}

export function PostClaimsBlock({ claims }: PostClaimsBlockProps) {
  if (claims.length === 0) return null;

  return (
    <div className="mt-4 border-l-2 border-border-default pl-4">
      <p className="text-xs font-medium text-text-muted mb-2">Key Claims</p>
      <ol className="space-y-1.5">
        {claims.map((claim, i) => (
          <li key={i} className="text-sm text-text-secondary">
            <span className="text-text-muted mr-1.5">{i + 1}.</span>
            {claim}
          </li>
        ))}
      </ol>
    </div>
  );
}
