import { Pill } from "./ui";

export function AppHeader({
  materialCount,
}: {
  materialCount: number;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-[1440px] items-center gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-slate-950 font-mono text-sm font-extrabold text-white">
            TP
          </div>
          <div className="min-w-0">
            <strong className="block truncate text-lg font-bold leading-tight text-slate-950">TripProof</strong>
            <span className="hidden truncate text-sm text-slate-500 sm:block">자료함에 묻고, 원문 근거로 확인합니다</span>
          </div>
        </div>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <Pill className="border-blue-200 bg-blue-50 text-blue-700">자료 {materialCount}</Pill>
        </div>
      </div>
    </header>
  );
}
