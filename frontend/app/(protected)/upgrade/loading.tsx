import { Skeleton } from "@/components/ui/skeleton";

export default function UpgradeLoading() {
  return (
    <div className="mx-auto w-full min-w-0 max-w-[880px] px-5 sm:px-6 py-16 sm:py-20 text-center">
      <Skeleton className="h-9 w-72 mx-auto" />
      <Skeleton className="mt-3 h-5 w-96 max-w-full mx-auto" />
      <div className="mt-12 grid gap-6 sm:grid-cols-2 max-w-[880px] mx-auto">
        <Skeleton className="h-[420px] w-full rounded-lg" />
        <Skeleton className="h-[420px] w-full rounded-lg" />
      </div>
    </div>
  );
}
