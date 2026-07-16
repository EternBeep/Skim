export function TextShimmer({ text, className = "" }) {
  return (
    <span className={`text-shimmer ${className}`}>
      {text}
    </span>
  );
}
