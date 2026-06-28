import { forwardRef } from "react";
import { cn } from "../../lib/utils";

const VARIANTS = {
  primary:
    "bg-accent text-primary font-semibold shadow-glow-sm hover:shadow-glow hover:-translate-y-0.5 active:translate-y-0",
  secondary:
    "bg-surface-raised text-ink border border-white/10 hover:border-accent/40 hover:-translate-y-0.5 active:translate-y-0",
  ghost: "bg-transparent text-ink hover:bg-white/5",
  outline:
    "bg-transparent border border-accent/40 text-accent hover:bg-accent/10",
};

const SIZES = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-14 px-8 text-base",
  icon: "h-10 w-10",
};

export const Button = forwardRef(
  (
    { className, variant = "primary", size = "md", disabled, children, ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-xl2 font-display tracking-tight transition-all duration-200 ease-out",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
          "disabled:opacity-40 disabled:pointer-events-none disabled:translate-y-0",
          VARIANTS[variant],
          SIZES[size],
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
