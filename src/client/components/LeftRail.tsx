import { FileText, Upload } from "lucide-react";
import { useRef } from "react";
import type { LibraryItem } from "../types";
import { Button, Panel, PanelHeader, Pill } from "./ui";

export function LeftRail({
  isUploading,
  materials,
  onUploadMaterial,
}: {
  isUploading: boolean;
  materials: LibraryItem[];
  onUploadMaterial: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <aside className="grid content-start gap-4 lg:sticky lg:top-20">
      <Panel>
        <div className="p-4">
          <div className="text-xl font-extrabold text-slate-950">자료함</div>
          <div className="mt-1 text-sm leading-6 text-slate-500">
            예약 확인서와 안내문을 모아두고, 필요한 순간에 원문을 확인합니다.
          </div>
          <Button block className="mt-4" disabled={isUploading} onClick={() => inputRef.current?.click()} variant="primary">
            <Upload size={16} />
            {isUploading ? "업로드 중" : "PDF 추가"}
          </Button>
          <input
            ref={inputRef}
            accept="application/pdf,.pdf"
            className="sr-only"
            type="file"
            onChange={(event) => {
              const [file] = Array.from(event.target.files ?? []);
              event.target.value = "";
              if (file) {
                onUploadMaterial(file);
              }
            }}
          />
        </div>
      </Panel>

      <Panel>
        <PanelHeader aside={<span className="text-xs font-medium text-slate-500">{materials.length}개</span>}>
          <h2 className="text-sm font-bold text-slate-950">원문 자료</h2>
        </PanelHeader>
        <div className="p-3">
          {materials.length === 0 ? (
            <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
              <FileText className="mx-auto text-slate-400" size={28} />
              <strong className="mt-3 block text-sm text-slate-900">아직 자료가 없습니다</strong>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                예약 확인서나 안내문을 추가하면 이곳에서 원문을 관리합니다.
              </p>
            </div>
          ) : (
            <div className="grid gap-2">
              {materials.map((material) => (
                <button
                  className="flex min-w-0 items-start gap-3 rounded-md px-2 py-2.5 text-left transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  key={material.id}
                >
                  <span className="mt-0.5 inline-flex h-7 min-w-10 items-center justify-center rounded bg-slate-900 px-2 font-mono text-[11px] font-bold text-white">
                    PDF
                  </span>
                  <span className="min-w-0">
                    <strong className="block truncate text-sm text-slate-900">{material.name}</strong>
                    <span className="block truncate text-xs text-slate-500">{material.fileName}</span>
                    {material.status === "ready" && material.pageCount ? (
                      <span className="mt-1 block text-xs text-slate-500">{material.pageCount}쪽</span>
                    ) : null}
                    {material.status === "failed" && material.error ? (
                      <span className="mt-1 block text-xs leading-5 text-rose-700">{material.error}</span>
                    ) : null}
                    <span className="mt-2 block">
                      <MaterialStatus item={material} />
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </Panel>
    </aside>
  );
}

function MaterialStatus({ item }: { item: LibraryItem }) {
  const labels: Record<LibraryItem["status"], string> = {
    ready: "읽기 완료",
    failed: "읽기 실패",
  };
  const classes: Record<LibraryItem["status"], string> = {
    ready: "border-emerald-200 bg-emerald-50 text-emerald-700",
    failed: "border-rose-200 bg-rose-50 text-rose-700",
  };

  return <Pill className={classes[item.status]}>{labels[item.status]}</Pill>;
}
