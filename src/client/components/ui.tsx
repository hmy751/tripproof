import { AlertTriangle, Check, ShieldAlert } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { EvidenceState } from "../../shared/tripFacts";
import type { CardDecision } from "../data/tripSession";
import { evidenceLabels, evidencePillClasses, sourceLabels, sourcePillClasses } from "../lib/tripUi";

export function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Panel({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section className={cx("rounded-lg border border-slate-200 bg-white shadow-sm", className)} id={id}>
      {children}
    </section>
  );
}

export function PanelHeader({
  aside,
  children,
}: {
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
      <div className="min-w-0">{children}</div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}

export function Button({
  block = false,
  children,
  className,
  size = "md",
  variant = "secondary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  block?: boolean;
  size?: "sm" | "md";
  variant?: "primary" | "secondary" | "ghost" | "danger";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-md border font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50";
  const sizes = {
    sm: "min-h-8 px-2.5 text-xs",
    md: "min-h-10 px-3 text-sm",
  };
  const variants = {
    primary: "border-blue-600 bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border-slate-300 bg-white text-slate-800 hover:bg-slate-50",
    ghost: "border-transparent bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900",
    danger: "border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100",
  };

  return (
    <button className={cx(base, sizes[size], variants[variant], block && "w-full", className)} {...props}>
      {children}
    </button>
  );
}

export function Pill({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cx(
        "inline-flex min-h-6 items-center gap-1.5 rounded-full border px-2 text-xs font-medium leading-none",
        className ?? "border-slate-200 bg-white text-slate-600",
      )}
    >
      {children}
    </span>
  );
}

export function EvidencePill({ state }: { state: EvidenceState }) {
  const Icon = state === "supported" ? Check : state === "missing" || state === "conflict" ? AlertTriangle : ShieldAlert;
  return (
    <Pill className={evidencePillClasses[state]}>
      <Icon size={14} />
      {evidenceLabels[state]}
    </Pill>
  );
}

export function SourcePill({ source }: { source: CardDecision["source"] }) {
  return <Pill className={sourcePillClasses[source]}>{sourceLabels[source]}</Pill>;
}
