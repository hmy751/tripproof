import { candidateCards, tripSession } from "../data/tripSession";
import { Pill } from "./ui";

export function AppHeader({
  boardCount,
  fieldCount,
}: {
  boardCount: number;
  fieldCount: number;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-[1680px] items-center gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-slate-950 font-mono text-sm font-extrabold text-white">
            TP
          </div>
          <div className="min-w-0">
            <strong className="block truncate text-lg font-bold leading-tight text-slate-950">TripProof</strong>
            <span className="hidden truncate text-sm text-slate-500 sm:block">자료에 묻고, 근거 있는 답변만 남깁니다</span>
          </div>
        </div>

        <select
          aria-label="여행 선택"
          className="hidden h-10 rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-800 lg:block"
          defaultValue="osaka"
        >
          <option value="osaka">오사카 4박 5일 · 출발 D-3</option>
          <option value="tokyo">도쿄 체크인 테스트 여행</option>
        </select>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <Pill className="border-blue-200 bg-blue-50 text-blue-700">자료 {tripSession.artifacts.length}</Pill>
          <Pill className="border-amber-200 bg-amber-50 text-amber-800">후보 {candidateCards.length}</Pill>
          <Pill className="border-emerald-200 bg-emerald-50 text-emerald-700">대시보드 {boardCount}</Pill>
          <Pill className="border-violet-200 bg-violet-50 text-violet-700">현장 {fieldCount}</Pill>
        </div>
      </div>
    </header>
  );
}
