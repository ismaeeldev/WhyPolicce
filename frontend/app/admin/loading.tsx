import { Skeleton } from "@/components/ui/skeleton";

// Renders inside the admin shell (app/admin/layout.tsx) while a page loads,
// so admin routes never fall back to the root home-page skeleton.
export default function AdminLoading() {
  return (
    <div className="mx-auto w-full max-w-[1000px]">
      <Skeleton className="h-9 w-48 mb-6" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full rounded-md" />
        ))}
      </div>
    </div>
  );
}
