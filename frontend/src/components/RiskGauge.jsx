import React from "react";

// Simple SVG semicircle gauge
export default function RiskGauge({ score = 0, level = "low" }) {
  const v = Math.max(0, Math.min(100, score));
  const angle = (v / 100) * 180; // 0..180
  const r = 80;
  const cx = 100;
  const cy = 100;
  const start = polar(cx, cy, r, 180);
  const end = polar(cx, cy, r, 180 + angle);
  const large = angle > 180 ? 1 : 0;
  const arc = `M ${start.x} ${start.y} A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`;

  const color = {
    critical: "#EF4444",
    high: "#F59E0B",
    medium: "#3B82F6",
    low: "#10B981",
  }[level] || "#10B981";

  return (
    <div className="flex flex-col items-center justify-center anim-fade" data-testid="risk-gauge">
      <svg width="200" height="120" viewBox="0 0 200 120">
        <path d={`M 20 100 A 80 80 0 0 1 180 100`} stroke="#1F2937" strokeWidth="12" fill="none" />
        <path d={arc} stroke={color} strokeWidth="12" fill="none" strokeLinecap="butt" />
        <text x="100" y="92" textAnchor="middle" fill="#F9FAFB" fontFamily="JetBrains Mono" fontWeight="700" fontSize="32">{v}</text>
        <text x="100" y="110" textAnchor="middle" fill="#9CA3AF" fontFamily="JetBrains Mono" fontSize="9" letterSpacing="2">/ 100</text>
      </svg>
      <div className={`mt-1 font-mono text-xs uppercase tracking-[0.3em]`} style={{ color }}>
        {level} RISK
      </div>
    </div>
  );
}

function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
