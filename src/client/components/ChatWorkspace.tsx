import { FileText, Send } from "lucide-react";
import type { ChatMessage } from "../types";
import { Button, Panel, PanelHeader, cx } from "./ui";

export function ChatWorkspace({
  materialCount,
  messages,
  question,
  onAsk,
  onQuestionChange,
}: {
  materialCount: number;
  messages: ChatMessage[];
  question: string;
  onAsk: (question?: string) => void;
  onQuestionChange: (value: string) => void;
}) {
  const isLibraryEmpty = materialCount === 0;

  return (
    <Panel className="overflow-hidden">
      <PanelHeader>
        <h1 className="text-sm font-bold text-slate-950">자료함 채팅</h1>
        <p className="mt-0.5 text-xs text-slate-500">
          {isLibraryEmpty ? "질문할 자료가 아직 없습니다" : `전체 자료함 ${materialCount}개 대상`}
        </p>
      </PanelHeader>

      <div className="grid min-h-[520px] content-start gap-4 overflow-y-auto px-4 py-4">
        {isLibraryEmpty ? <EmptyLibraryState /> : null}

        {!isLibraryEmpty && messages.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center">
            <strong className="block text-sm text-slate-900">아직 질문이 없습니다</strong>
            <p className="mt-1 text-sm text-slate-500">자료 전체를 대상으로 확인할 내용을 물어보세요.</p>
          </div>
        ) : null}

        {messages.map((message) =>
          message.role === "user" ? (
            <div className="flex justify-end" key={message.id}>
              <div className="max-w-[78%] rounded-lg bg-slate-950 px-4 py-3 text-sm leading-6 text-white">{message.text}</div>
            </div>
          ) : (
            <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3" key={message.id}>
              <div className="grid h-8 w-8 place-items-center rounded-full bg-slate-950 font-mono text-[11px] font-bold text-white">
                TP
              </div>
              <div
                className={cx(
                  "rounded-lg border px-4 py-3 text-sm leading-6",
                  message.tone === "blocked"
                    ? "border-amber-200 bg-amber-50 text-amber-900"
                    : "border-slate-200 bg-white text-slate-700",
                )}
              >
                <div>{message.text}</div>
                {message.meta ? <div className="mt-2 text-xs font-medium text-slate-500">{message.meta}</div> : null}
                {message.excerpt ? (
                  <blockquote className="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
                    {message.excerpt}
                  </blockquote>
                ) : null}
              </div>
            </div>
          ),
        )}
      </div>

      <div className="border-t border-slate-200 bg-white p-3">
        <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
          <textarea
            aria-label="자료함에 질문"
            className="min-h-20 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 disabled:text-slate-400"
            disabled={isLibraryEmpty}
            placeholder={isLibraryEmpty ? "자료를 먼저 추가하세요" : "이번 여행 자료에 대해 물어보세요"}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onAsk();
              }
            }}
          />
          <Button className="md:h-full md:min-w-28" disabled={isLibraryEmpty} onClick={() => onAsk()} variant="primary">
            <Send size={16} />
            물어보기
          </Button>
        </div>
      </div>
    </Panel>
  );
}

function EmptyLibraryState() {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
      <FileText className="mx-auto text-slate-400" size={36} />
      <strong className="mt-4 block text-base text-slate-950">자료함이 비어 있습니다</strong>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
        예약 확인서나 호스트 안내문을 추가하면 자료 전체를 대상으로 질문할 수 있습니다.
      </p>
    </div>
  );
}
