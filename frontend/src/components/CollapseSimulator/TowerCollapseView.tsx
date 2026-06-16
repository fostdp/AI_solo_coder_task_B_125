import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

export const FLOOR_COLORS = ['#ff4d4f', '#fa8c16', '#fadb14', '#52c41a', '#1890ff'];

export interface CollapseViewProps {
  floorCount: number;
  floorHeights: number[];
  floorDiameters: number[];
  displacements: number[];
  damageIndices: number[];
  collapsedFloors: boolean[];
  failureSequence: any[];
  currentTime: number;
}

const TowerCollapseView: React.FC<CollapseViewProps> = ({
  floorCount, floorHeights, floorDiameters, displacements, damageIndices, collapsedFloors, failureSequence, currentTime
}) => {
  const scale = 280 / (floorHeights.reduce((a, b) => a + b, 0) * 1.3);
  const cumH: number[] = [];
  let s = 0;
  floorHeights.forEach(h => { cumH.push(s * scale); s += h; });
  const maxD = Math.max(...floorDiameters);
  const dScale = 220 / (maxD * 1.4);

  const floorElems = [];
  for (let f = 0; f < floorCount; f++) {
    const h = floorHeights[f] * scale;
    const d = floorDiameters[f] * dScale;
    const bottom = 30 + cumH[f];
    const dispX = displacements[f] * 0.5;
    const dmg = damageIndices[f] || 0;
    const collapsed = collapsedFloors[f] || false;

    const opacity = collapsed ? 0.45 : 1;
    const tilt = collapsed ? (displacements[f] > 0 ? 8 : -8) : 0;
    const vertSquash = collapsed ? Math.max(0.3, 1 - dmg * 0.4) : 1;

    const fillColor = dmg < 0.3 ? '#A0522D' : dmg < 0.6 ? '#CD853F' : dmg < 0.85 ? '#D4612B' : '#8B0000';

    floorElems.push(
      <g key={f} style={{ transition: 'all .25s ease' }}
         transform={`translate(${dispX}, 0) rotate(${tilt}, 240, ${bottom + h / 2 * vertSquash})`}>
        <rect x={240 - d / 2} y={bottom + h * (1 - vertSquash)} width={d} height={h * vertSquash}
              fill={fillColor} opacity={opacity} stroke="#3d1f0a" strokeWidth={1.5} rx={2} />
        <rect x={240 - d * 0.58} y={bottom - 8} width={d * 1.16} height={12}
              fill="#8B0000" opacity={opacity} stroke="#5a0000" strokeWidth={1} />
        {[0, 1, 2, 3, 4, 5, 6, 7].map(i => (
          <rect key={i}
                x={240 - d / 2 + 5 + i * (d - 10) / 8}
                y={bottom + h * (1 - vertSquash) + 6}
                width={3} height={Math.max(6, (h * vertSquash) - 12)}
                fill="#6B3A0F" opacity={opacity * 0.9} />
        ))}
        {collapsed && (
          <>
            {Array.from({ length: 6 }).map((_, i) => (
              <polygon key={`d-${f}-${i}`}
                       points={`${240 - d / 2 + Math.random() * d},${bottom + h * (1 - vertSquash) + h * vertSquash * 0.5} ${240 - d / 2 + Math.random() * d + 15},${bottom + h * (1 - vertSquash) + h * vertSquash * 0.5} ${240 - d / 2 + Math.random() * d + 8},${bottom + h * (1 - vertSquash) + h * vertSquash * 0.5 + 25}`}
                       fill="#8B4513" opacity={0.85 - i * 0.1} />
            ))}
          </>
        )}
        <circle cx={240} cy={bottom + h * vertSquash * 0.5} r={16}
                fill="#fff" opacity={0.9} stroke={FLOOR_COLORS[f]} strokeWidth={2} />
        <text x={240} y={bottom + h * vertSquash * 0.5 + 4} textAnchor="middle"
              fontSize={11} fontWeight="bold" fill={FLOOR_COLORS[f]}>{f + 1}F</text>
        {dmg > 0.1 && (
          <rect x={240 - d / 2} y={bottom + h * vertSquash - 6} width={d * Math.min(1, dmg)} height={4}
                fill={FLOOR_COLORS[Math.min(4, Math.floor(dmg * 5))]} opacity={0.85} />
        )}
      </g>
    );
  }

  return (
    <svg viewBox="0 0 480 400" style={{ width: '100%', height: 420, background: 'linear-gradient(180deg,#e6f2ff 0%,#f7f9fc 70%,#eef5e6 100%)', borderRadius: 8 }}>
      <defs>
        <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a8a39b" />
          <stop offset="100%" stopColor="#8a857e" />
        </linearGradient>
      </defs>
      <rect x="0" y="385" width="480" height="20" fill="url(#ground)" />
      <line x1="30" y1="385" x2="30" y2="80" stroke="#999" strokeWidth="1" strokeDasharray="4,4" />
      {[0, 1, 2, 3, 4].map(i => (
        <text key={i} x={20} y={385 - (i * 80)} fontSize={10} fill="#666" textAnchor="end">{i * 16}m</text>
      ))}
      {floorElems}
      {failureSequence.slice(0, 5).map((ev, i) => (
        <g key={`fe-${i}`}>
          <line x1={420} y1={80 + i * 20} x2={395} y2={80 + i * 20} stroke={ev.event_type.includes('collapse') ? '#ff4d4f' : '#faad14'} strokeWidth={2} />
          <text x={425} y={84 + i * 20} fontSize={10} fill="#333">
            {ev.floor}层 {ev.time.toFixed(1)}s ({(ev.drift_ratio * 100).toFixed(1)}%)
          </text>
        </g>
      ))}
      <text x={240} y={24} textAnchor="middle" fontSize={13} fill="#333">
        实时倒塌过程模拟 · t = <Text strong>{currentTime.toFixed(2)}s</Text>
      </text>
    </svg>
  );
};

export default TowerCollapseView;
