import type { ReactNode } from "react";
import type { View } from "../types";
import { cx } from "./ui";

export function ViewTabs({
  activeView,
  onChange,
}: {
  activeView: View;
  onChange: (view: View) => void;
}) {
  return (
    <nav aria-label="TripProof 화면" className="grid grid-cols-3 rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
      <TabButton active={activeView === "ask"} onClick={() => onChange("ask")}>
        확인
      </TabButton>
      <TabButton active={activeView === "board"} onClick={() => onChange("board")}>
        대시보드
      </TabButton>
      <TabButton active={activeView === "field"} onClick={() => onChange("field")}>
        현장
      </TabButton>
    </nav>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      className={cx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
        active ? "bg-slate-950 text-white shadow-sm" : "text-slate-600 hover:bg-slate-50 hover:text-slate-950",
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
