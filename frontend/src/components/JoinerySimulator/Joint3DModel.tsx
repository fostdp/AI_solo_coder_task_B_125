import React from 'react';

export interface JointType {
  id: string;
  name: string;
  chinese_name: string;
  category: string;
  elastic_stiffness: number;
  yield_moment: number;
  ultimate_moment: number;
  yield_rotation: number;
  ultimate_rotation: number;
  damping_ratio: number;
  pinching_factor: number;
  model_type: string;
  ductility?: number;
}

export const CATEGORY_COLORS: Record<string, string> = {
  beam_column: '#D4612B',
  cross_joint: '#2B61D4',
  through_beam: '#52c41a',
  bracing: '#722ed1',
  bracket_set: '#fa8c16'
};

export const CATEGORY_NAMES: Record<string, string> = {
  beam_column: '梁柱连接',
  cross_joint: '十字交叉',
  through_beam: '贯穿梁',
  bracing: '斜撑连接',
  bracket_set: '斗拱节点'
};

export interface Joint3DModelProps {
  type: JointType;
}

const Joint3DModel: React.FC<Joint3DModelProps> = ({ type }) => {
  const id = type.id;
  const base = '#A0522D';
  const accent = '#8B4513';
  const common = (
    <>
      <defs>
        <linearGradient id={`g-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#CD853F" />
          <stop offset="50%" stopColor={base} />
          <stop offset="100%" stopColor={accent} />
        </linearGradient>
        <filter id={`s-${id}`}>
          <feDropShadow dx="2" dy="4" stdDeviation="3" floodOpacity="0.3" />
        </filter>
      </defs>
    </>
  );
  let body: React.ReactNode = null;
  if (id === 'straight_tenon') {
    body = (
      <>
        <rect x="80" y="150" width="180" height="80" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="3" filter={`url(#s-${id})`} />
        <path d="M 260 150 L 260 230 L 340 220 L 340 160 Z" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <rect x="260" y="168" width="70" height="44" fill="#fff8dc" opacity="0.35" />
        <path d="M 260 175 L 320 170" stroke="#5a2e0f" strokeWidth="0.8" strokeDasharray="2,2" />
      </>
    );
  } else if (id === 'dovetail_tenon') {
    body = (
      <>
        <rect x="70" y="150" width="170" height="80" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="3" filter={`url(#s-${id})`} />
        <polygon points="240,150 340,170 360,190 340,210 240,230 255,190" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <polygon points="240,165 335,182 348,190 335,198 240,215 252,190" fill="#fff8dc" opacity="0.35" />
      </>
    );
  } else if (id === 'cross_tenon') {
    body = (
      <>
        <rect x="50" y="160" width="320" height="60" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="2" filter={`url(#s-${id})`} />
        <rect x="180" y="80" width="60" height="220" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="2" opacity="0.85" />
        <rect x="180" y="160" width="60" height="30" fill="none" stroke="#fff" strokeWidth="1.5" strokeDasharray="3,2" />
      </>
    );
  } else if (id === 'through_tenon') {
    body = (
      <>
        <ellipse cx="210" cy="190" rx="75" ry="80" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" filter={`url(#s-${id})`} />
        <rect x="70" y="175" width="280" height="30" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="2" />
        <rect x="340" y="170" width="12" height="40" fill="#3d1f0a" />
        <polygon points="340,175 360,170 360,210 340,205" fill="#8B4513" stroke="#3d1f0a" strokeWidth="1" />
        <text x="352" y="225" textAnchor="middle" fontSize="10" fill="#3d1f0a">木楔</text>
      </>
    );
  } else if (id === 'angle_brace_tenon') {
    body = (
      <>
        <rect x="70" y="220" width="280" height="50" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" rx="2" filter={`url(#s-${id})`} />
        <polygon points="120,220 300,100 320,110 140,230" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <circle cx="130" cy="225" r="5" fill="#3d1f0a" />
        <circle cx="310" cy="105" r="5" fill="#3d1f0a" />
        <text x="220" y="165" textAnchor="middle" fontSize="11" fill="#3d1f0a" fontWeight="bold">45° 斜撑</text>
      </>
    );
  } else if (id === 'bucket_arch_joint') {
    body = (
      <>
        <rect x="160" y="260" width="80" height="30" fill="#6B3A0F" stroke="#3d1f0a" strokeWidth="1.5" filter={`url(#s-${id})`} />
        <rect x="130" y="225" width="140" height="35" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <rect x="155" y="195" width="90" height="30" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <rect x="100" y="160" width="200" height="35" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <rect x="170" y="130" width="60" height="30" fill={`url(#g-${id})`} stroke="#5a2e0f" strokeWidth="1.5" />
        <rect x="120" y="90" width="160" height="40" fill="#8B0000" stroke="#5a2e0f" strokeWidth="1.5" />
        {[0, 1, 2, 3].map(i => (
          <React.Fragment key={i}>
            <circle cx={145 + i * 38} cy={205} r="8" fill="#CD853F" stroke="#3d1f0a" strokeWidth="1" />
          </React.Fragment>
        ))}
      </>
    );
  }
  return (
    <svg viewBox="0 0 420 310" style={{ width: '100%', background: 'linear-gradient(135deg,#faf6f0 0%,#f5ebe0 100%)', borderRadius: 8 }}>
      {common}
      {body}
    </svg>
  );
};

export default Joint3DModel;
