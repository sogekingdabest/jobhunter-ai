export interface SkeletonProps {
  height?: string;
  label?: string;
  width?: string;
}

export function Skeleton({ height = "1rem", label = "Loading content", width = "100%" }: SkeletonProps) {
  return (
    <span aria-label={label} className="ds-skeleton-wrap" role="status">
      <span
        aria-hidden="true"
        className="ds-skeleton"
        style={{ height, width }}
      />
    </span>
  );
}
