interface PostQuestionsBlockProps {
  questions: string[];
}

export function PostQuestionsBlock({ questions }: PostQuestionsBlockProps) {
  if (questions.length === 0) return null;

  return (
    <div className="mt-3 border-l-2 border-border-default pl-4">
      <p className="text-xs font-medium text-text-muted mb-2">Questions Raised</p>
      <ul className="space-y-1.5">
        {questions.map((question, i) => (
          <li key={i} className="text-sm text-text-accent">
            <span className="mr-1.5">?</span>
            {question}
          </li>
        ))}
      </ul>
    </div>
  );
}
