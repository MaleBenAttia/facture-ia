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
          33% { transform: translate(40px, -60px) rotate(45deg); }
          66% { transform: translate(-30px, 40px) rotate(-30deg); }
          100% { transform: translate(0, 0) rotate(0deg); }
        }
      `}</style>

      {iconsData.map(({ id, Icon, left, top, size, rotation, animDuration, animDelay }) => (
        <div
          key={id}
          className="absolute text-slate-900 opacity-[0.04]"
          style={{
            left,
            top,
            width: size,
            height: size,
            animation: `float-icon ${animDuration}s infinite ease-in-out`,
            animationDelay: `${animDelay}s`,
          }}
        >
          <Icon strokeWidth={1.5} className="w-full h-full" style={{ transform: `rotate(${rotation}deg)` }} />
        </div>
      ))}
      
      {/* Léger grain ou gradient pour habiller le fond sans être uni */}
      <div 
        className="absolute inset-0 opacity-[0.4]"
        style={{
          background: "radial-gradient(circle at 50% 50%, rgba(200,200,200,0.05) 0%, rgba(0,0,0,0.03) 100%)",
        }}
      />
    </div>
  );
}
