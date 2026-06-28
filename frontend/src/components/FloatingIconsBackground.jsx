import React, { useMemo } from "react";
import { Wrench, Settings, Gauge, PenTool, Hexagon, CircleDashed, Car, Compass, Activity, Crosshair } from "lucide-react";

const ICONS = [Wrench, Settings, Gauge, PenTool, Hexagon, CircleDashed, Car, Compass, Activity, Crosshair];

/**
 * Génère des positions et timings aléatoires pour les icônes
 */
function generateRandomIcons(count) {
  return Array.from({ length: count }).map((_, i) => {
    const Icon = ICONS[i % ICONS.length];
    return {
      id: i,
      Icon,
      left: `${Math.random() * 90 + 5}%`,
      top: `${Math.random() * 90 + 5}%`,
      size: Math.random() * 30 + 40, // 40px à 70px
      rotation: Math.random() * 360,
      animDuration: Math.random() * 20 + 20, // 20s à 40s
      animDelay: Math.random() * -20, // décalage initial
    };
  });
}

export function FloatingIconsBackground() {
  const iconsData = useMemo(() => generateRandomIcons(15), []);

  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none bg-[var(--color-bg)]">
      
      <style>{`
        @keyframes float-icon {
          0% { transform: translate(0, 0) rotate(0deg); }
          25% { transform: translate(15px, -20px) rotate(15deg); }
          50% { transform: translate(-10px, 15px) rotate(-10deg); }
          75% { transform: translate(-20px, -15px) rotate(-20deg); }
          100% { transform: translate(0, 0) rotate(0deg); }
        }
      `}</style>

      {iconsData.map(({ id, Icon, left, top, size, rotation, animDuration, animDelay }) => (
        <div
          key={id}
          className="absolute text-slate-400 opacity-[0.08]"
          style={{
            left,
            top,
            width: size,
            height: size,
            transform: `rotate(${rotation}deg)`,
            animation: `float-icon ${animDuration}s infinite ease-in-out`,
            animationDelay: `${animDelay}s`,
          }}
        >
          <Icon strokeWidth={1.5} className="w-full h-full" />
        </div>
      ))}
      
      {/* Léger grain ou gradient pour habiller le fond sans être uni */}
      <div 
        className="absolute inset-0 opacity-[0.3]"
        style={{
          background: "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.03) 100%)",
        }}
      />
    </div>
  );
}
