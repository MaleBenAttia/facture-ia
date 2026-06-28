import { cn } from "../../lib/utils";

export function Card({ className, children, glow = false, ...props }) {
  return (
    <div
      className={cn(
        "rounded-xl2 border border-white/8 bg-surface-raised/80 backdrop-blur-sm shadow-card",
        glow && "shadow-glow-sm",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }) {
  return (
    <div className={cn("p-5 pb-3 flex items-center justify-between gap-3", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }) {
  return (
    <h3
      className={cn("font-display text-base font-semibold text-ink tracking-tight", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardContent({ className, children, ...props }) {
  return (
    <div className={cn("p-5 pt-0", className)} {...props}>
      {children}
    </div>
  );
}
