import { ListChecks } from "lucide-react";
import { Button, Panel, PanelHeader, Pill } from "./ui";

export function RecommendationRail({ materialCount }: { materialCount: number }) {
  return (
    <aside className="grid content-start gap-4 lg:sticky lg:top-20">
      <Panel>
        <PanelHeader aside={<Pill className="border-slate-200 bg-slate-50 text-slate-600">0</Pill>}>
          <h2 className="text-sm font-bold text-slate-950">추천 확인 항목</h2>
          <p className="mt-0.5 text-xs text-slate-500">자료에서 먼저 확인할 만한 내용</p>
        </PanelHeader>
        <div className="p-3">
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
            <ListChecks className="mx-auto text-slate-400" size={28} />
            <strong className="mt-3 block text-sm text-slate-900">아직 추천 항목이 없습니다</strong>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              {materialCount === 0
                ? "자료를 추가하면 확인할 만한 항목을 이곳에 정리합니다."
                : "자료를 읽은 뒤 확인할 만한 항목을 이곳에 정리합니다."}
            </p>
            <Button block className="mt-4" disabled>
              카드 초안으로
            </Button>
          </div>
        </div>
      </Panel>
    </aside>
  );
}
