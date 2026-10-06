import { Skeleton } from "@/components/ui/skeleton";

// Route-level fallback so /inquiries/new doesn't inherit the home-page
// skeleton from app/loading.tsx.
export default function NewInquiryLoading() {
  return (
    <div className="mx-auto w-full max-w-[760px] px-5 sm:px-6 py-12 sm:py-16 space-y-5">
      <Skeleton className="h-9 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-40 w-full" />
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
      <Skeleton className="h-11 w-40" />
    </div>
  );
}
