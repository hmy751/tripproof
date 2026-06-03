import { ClipboardList } from "lucide-react";
import { Button, Panel, PanelHeader, Pill } from "./ui";

export function DraftListPanel() {
  return (
    <Panel>
      <PanelHeader aside={<Pill className="border-slate-200 bg-slate-50 text-slate-600">0</Pill>}>
        <h2 className="text-sm font-bold text-slate-950">카드 초안</h2>
        <p className="mt-0.5 text-xs text-slate-500">확인한 답변을 카드로 올리기 전 검토합니다</p>
      </PanelHeader>
      <div className="p-4">
        <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
          <ClipboardList className="mx-auto text-slate-400" size={32} />
          <strong className="mt-3 block text-sm text-slate-900">아직 초안이 없습니다</strong>
          <p className="mx-auto mt-1 max-w-md text-sm leading-6 text-slate-500">
            채팅 답변이나 추천 확인 항목에서 사용자가 남길 정보를 고르면 이곳에 카드 초안이 쌓입니다.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <Button disabled size="sm">
              대시보드에 올리기
            </Button>
            <Button disabled size="sm" variant="ghost">
              초안 비우기
            </Button>
          </div>
        </div>
      </div>
    </Panel>
  );
}
