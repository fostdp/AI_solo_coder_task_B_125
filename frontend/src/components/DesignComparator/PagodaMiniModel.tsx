import React from 'react';

export interface PagodaInfo {
  id: string;
  name: string;
  dynasty: string;
  country: string;
  height: number;
  floor_count: number;
  structural_type: string;
  floor_heights: number[];
  floor_diameters: number[];
  inner_diameters: number[];
  wall_thickness: number[];
  timber_properties: Record<string, number>;
  joint_properties: Record<string, number>;
  seismic_philosophy: string;
  shinbashira: boolean;
  shinbashira_diameter: number;
}

export interface PagodaMiniModelProps {
  info: PagodaInfo;
  color: string;
}

const PagodaMiniModel: React.FC<PagodaMiniModelProps> = ({ info, color }) => {
  const h = info.height;
  const scale = 300 / (h * 1.2);
  const floors = [];
  let y = 10;
  for (let i = 0; i < info.floor_count; i++) {
    const d = info.floor_diameters[i] * scale;
    const fh = info.floor_heights[i] * scale;
    floors.push(
      <g key={i}>
        <rect x={200 - d / 2} y={350 - y - fh} width={d} height={fh}
              fill={color} opacity={0.7} stroke="#333" strokeWidth={1} rx={2} />
        {info.inner_diameters[i] > 0 && (
          <rect x={200 - (info.inner_diameters[i] * scale) / 2} y={350 - y - fh}
                width={info.inner_diameters[i] * scale} height={fh}
                fill="none" stroke="#fff" strokeWidth={1} strokeDasharray="3,2" />
        )}
        {i < info.floor_count - 1 && (
          <polygon
            points={`${200 - d * 0.75},${350 - y} ${200 + d * 0.75},${350 - y} ${200 - d * 0.55},${350 - y - 12} ${200 + d * 0.55},${350 - y - 12}`}
            fill="#8B0000" opacity={0.85}
          />
        )}
        {i === info.floor_count - 1 && (
          <>
            <polygon points={`${200 - d * 0.6},${350 - y} ${200 + d * 0.6},${350 - y} ${200},${350 - y - 50}`}
                     fill="#8B0000" opacity={0.9} />
            <rect x={198} y={350 - y - 70} width={4} height={20} fill="#FFD700" />
          </>
        )}
      </g>
    );
    y += fh;
  }
  return (
    <svg viewBox="0 0 400 400" style={{ width: '100%', height: 280, background: '#fafafa' }}>
      {floors}
      {info.shinbashira && (
        <line x1={200} y1={350} x2={200} y2={350 - info.height * scale - 30}
              stroke="#B8860B" strokeWidth={Math.max(2, info.shinbashira_diameter * scale * 2)}
              strokeDasharray="4,2" opacity={0.8} />
      )}
      <text x={200} y={380} textAnchor="middle" fontSize={14} fill="#333" fontWeight="bold">
        {info.name}（{info.country}·{info.dynasty}）
      </text>
    </svg>
  );
};

export default PagodaMiniModel;
