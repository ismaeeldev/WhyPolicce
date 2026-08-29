import { Skeleton } from "@/components/ui/skeleton";

export default function BillingLoading() {
  return (
    <div className="mx-auto max-w-[560px] px-6 py-16 sm:py-20">
      <Skeleton className="h-4 w-32 mb-6" />
      <Skeleton className="h-8 w-24" />
      <div className="mt-6 rounded-md border border-border-default bg-bg-elevated p-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-4 w-20" />
            <Skeleton className="mt-2 h-5 w-16 rounded-full" />
          </div>
          <Skeleton className="h-10 w-10 rounded-full" />
        </div>
        <Skeleton className="mt-5 h-10 w-full rounded-sm" />
      </div>
    </div>
  );
}
