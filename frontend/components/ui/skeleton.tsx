import { cn } from "@/lib/utils";

/**
 * Shared shimmer skeleton primitive — AgentGuide/01_ThemeGuideline.md §4.9.
 * Every async surface composes its skeleton from this, sized to match its
 * loaded state exactly, so the loading -> loaded swap never shifts layout.
 */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("wp-skeleton rounded-md", className)}
      {...props}
    />
  );
}

export { Skeleton };
