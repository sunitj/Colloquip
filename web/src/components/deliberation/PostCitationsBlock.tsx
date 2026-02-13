interface PostCitationsBlockProps {
  citations: Array<{ document_id: string; title: string; relevance: number }>;
}

export function PostCitationsBlock({ citations }: PostCitationsBlockProps) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {citations.map((citation) => (
        <button
          key={citation.document_id}
          className="inline-flex items-center bg-bg-elevated rounded-radius-sm px-2 py-0.5 text-xs text-text-accent hover:bg-bg-overlay transition-colors cursor-pointer"
          title={`Relevance: ${Math.round(citation.relevance * 100)}%`}
        >
          {citation.title}
        </button>
      ))}
    </div>
  );
}
