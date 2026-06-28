import { cn } from "../../lib/utils";

const VARIANTS = {
  default: "bg-white/8 text-ink border-white/10",
  accent: "bg-accent/15 text-secondary-pale border-accent/30",
  success: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  danger: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export function Badge({ className, variant = "default", children, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium font-body",
        VARIANTS[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
