import React, { useState, useEffect, useMemo } from 'react';
import {
  Row, Col, Card, Table, Tag, Typography, Slider, Button, Space,
  Tabs, Divider, Progress, Empty, Spin, Statistic, Radio, Descriptions, Alert
} from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';

const { Title, Paragraph, Text } = Typography;

interface JointType {
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
  ductility: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  beam_column: '#D4612B',
  cross_joint: '#2B61D4',
  through_beam: '#52c41a',
  bracing: '#722ed1',
  bracket_set: '#fa8c16'
};

const CATEGORY_NAMES: Record<string, string> = {
  beam_column: '梁柱连接',
  cross_joint: '十字交叉',
  through_beam: '贯穿梁',
  bracing: '斜撑连接',
  bracket_set: '斗拱节点'
};

const Joint3DModel: React.FC<{ type: JointType }> = ({ type }) => {
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

const MortiseTenon: React.FC = () => {
  const [jointTypes, setJointTypes] = useState<JointType[]>([]);
  const [selectedId, setSelectedId] = useState<string>('straight_tenon');
  const [maxRotation, setMaxRotation] = useState(0.03);
  const [cycles, setCycles] = useState(3);
  const [loading, setLoading] = useState(true);
  const [simResult, setSimResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const load = async () => {
      const res = await api.get('/new/mortise/types');
      setJointTypes(res.data.joint_types);
      setLoading(false);
    };
    load();
  }, []);

  const selected = useMemo(() => jointTypes.find(j => j.id === selectedId), [jointTypes, selectedId]);

  useEffect(() => {
    if (!selected) return;
    const run = async () => {
      setRunning(true);
      try {
        const res = await api.post('/new/mortise/cyclic', {
          joint_type_id: selected.id,
          max_rotation: maxRotation,
          cycles,
          steps_per_cycle: 80
        });
        setSimResult(res.data);
      } finally {
        setRunning(false);
      }
    };
    run();
  }, [selected, maxRotation, cycles]);

  const hysteresisOption = (data: any) => {
    if (!data?.hysteresis_loop) return {};
    const h = data.hysteresis_loop;
    return {
      title: { text: '滞回曲线（M-θ关系）', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: 70, right: 30, top: 50, bottom: 60 },
      xAxis: { type: 'value', name: '转角 θ (rad)', nameLocation: 'middle', nameGap: 32, splitLine: { lineStyle: { type: 'dashed' } } },
      yAxis: { type: 'value', name: '弯矩 M (N·m)', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [{
        name: '循环加载',
        type: 'line',
        data: (h.rotation_array || []).map((r: number, i: number) => [r, (h.moment_array || [])[i]]),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: CATEGORY_COLORS[selected?.category || 'beam_column'] },
        areaStyle: { opacity: 0.12 }
      }]
    };
  };

  const backboneOption = (data: any) => {
    if (!data?.backbone_curve) return {};
    const b = data.backbone_curve;
    return {
      title: { text: '骨架曲线', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 30, top: 50, bottom: 60 },
      xAxis: { type: 'value', name: '转角 θ (rad)', nameLocation: 'middle', nameGap: 32, splitLine: { lineStyle: { type: 'dashed' } } },
      yAxis: { type: 'value', name: '弯矩 M (N·m)', splitLine: { lineStyle: { type: 'dashed' } } },
      series: [
        {
          name: '骨架曲线',
          type: 'line',
          data: (b.positive_branch_rotations || []).map((r: number, i: number) => [r, (b.positive_branch_moments || [])[i]]),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 3, color: CATEGORY_COLORS[selected?.category || 'beam_column'] }
        },
        {
          name: '屈服点',
          type: 'scatter',
          data: [[b.yield_rotation, b.yield_moment]],
          symbolSize: 14,
          itemStyle: { color: '#ff4d4f', borderColor: '#000', borderWidth: 1 },
          label: { show: true, formatter: '屈服', position: 'bottom', fontSize: 11 }
        },
        {
          name: '极限点',
          type: 'scatter',
          data: [[b.ultimate_rotation, b.ultimate_moment]],
          symbolSize: 14,
          itemStyle: { color: '#faad14', borderColor: '#000', borderWidth: 1 },
          label: { show: true, formatter: '极限', position: 'top', fontSize: 11 }
        }
      ]
    };
  };

  const stiffnessOption = (data: any) => {
    if (!data?.stiffness_degradation) return {};
    const s = data.stiffness_degradation;
    return {
      title: { text: '刚度退化曲线', left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 30, top: 40, bottom: 40 },
      xAxis: { type: 'category', data: s.degradation_ratios?.map((_: number, i: number) => `第${i + 1}次`) },
      yAxis: { type: 'value', name: '割线刚度比', min: 0, max: 1.1 },
      series: [{
        type: 'bar',
        data: s.degradation_ratios,
        itemStyle: { color: s.degradation_ratios?.map((r: number) => r > 0.7 ? '#52c41a' : r > 0.4 ? '#faad14' : '#ff4d4f') },
        label: { show: true, position: 'top', formatter: (p: any) => (p.value * 100).toFixed(0) + '%' }
      }]
    };
  };

  if (loading) return <div style={{ padding: 60, textAlign: 'center' }}><Spin size="large" tip="加载榫卯数据..." /></div>;

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        古代匠人榫卯工艺数字化复原
        <Tag color="gold" style={{ marginLeft: 12 }}>6 类经典榫卯</Tag>
      </Title>
      <Paragraph type="secondary">通过非线性弹簧模型真实还原各类榫卯节点的弯矩-转角滞回特性，支持捏缩效应、刚度退化、能量耗散分析</Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <Card title="榫卯类型" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {jointTypes.map(j => (
                <div key={j.id} onClick={() => setSelectedId(j.id)}
                     style={{ padding: 10, borderRadius: 6, cursor: 'pointer', border: selectedId === j.id ? `2px solid ${CATEGORY_COLORS[j.category]}` : '1px solid #f0f0f0', background: selectedId === j.id ? '#fffbe6' : '#fff', transition: 'all .2s' }}>
                  <Row>
                    <Col span={20}>
                      <Text strong>{j.chinese_name}</Text>
                      <div style={{ fontSize: 12 }}>
                        <Tag color={CATEGORY_COLORS[j.category]} style={{ margin: '2px 0' }}>{CATEGORY_NAMES[j.category]}</Tag>
                        <Tag>延性 μ={(j.ultimate_rotation / j.yield_rotation).toFixed(1)}</Tag>
                      </div>
                    </Col>
                    <Col span={4} style={{ textAlign: 'right' }}>
                      <Progress type="dashboard" percent={Math.round(j.damping_ratio * 1000)} width={42} strokeColor={CATEGORY_COLORS[j.category]} />
                      <div style={{ fontSize: 10, color: '#999' }}>阻尼</div>
                    </Col>
                  </Row>
                </div>
              ))}
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card
            title={
              <Space>
                <Text strong style={{ color: CATEGORY_COLORS[selected?.category || 'beam_column'] }}>{selected?.chinese_name}</Text>
                <Tag>{selected?.model_type}</Tag>
              </Space>
            }
            extra={
              <Statistic title="延性系数" value={(selected?.ultimate_rotation! / selected?.yield_rotation!).toFixed(2)} valueStyle={{ color: CATEGORY_COLORS[selected?.category || 'beam_column'], fontSize: 16 }} />
            }
          >
            <Joint3DModel type={selected!} />
            <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
              <Descriptions.Item label="弹性刚度">{selected?.elastic_stiffness.toExponential(2)} N·m/rad</Descriptions.Item>
              <Descriptions.Item label="屈服弯矩">{selected?.yield_moment.toLocaleString()} N·m</Descriptions.Item>
              <Descriptions.Item label="极限弯矩">{selected?.ultimate_moment.toLocaleString()} N·m</Descriptions.Item>
              <Descriptions.Item label="屈服转角">{selected?.yield_rotation.toFixed(4)} rad</Descriptions.Item>
              <Descriptions.Item label="极限转角">{selected?.ultimate_rotation.toFixed(4)} rad</Descriptions.Item>
              <Descriptions.Item label="捏缩系数">{selected?.pinching_factor.toFixed(2)}</Descriptions.Item>
            </Descriptions>
            <Divider style={{ margin: '12px 0' }} />
            <Title level={5}>加载参数</Title>
            <Row gutter={12}>
              <Col span={14}>
                <Text style={{ fontSize: 12 }}>最大转角 θ_max = {maxRotation.toFixed(3)} rad ({(maxRotation * 180 / Math.PI).toFixed(2)}°)</Text>
                <Slider min={0.005} max={0.08} step={0.001} value={maxRotation} onChange={setMaxRotation} />
              </Col>
              <Col span={10}>
                <Text style={{ fontSize: 12 }}>循环次数 = {cycles}</Text>
                <Slider min={1} max={8} step={1} value={cycles} onChange={setCycles} />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="力学性能对比（6类榫卯）" size="small">
            <ReactECharts
              option={{
                title: { text: '弯矩能力与延性', left: 'center', textStyle: { fontSize: 13 } },
                tooltip: { trigger: 'axis' },
                legend: { bottom: 0 },
                grid: { left: 60, right: 40, top: 40, bottom: 60 },
                xAxis: { type: 'category', data: jointTypes.map(j => j.chinese_name) },
                yAxis: [
                  { type: 'value', name: '极限弯矩 (10⁴N·m)' },
                  { type: 'value', name: '延性系数' }
                ],
                series: [
                  { name: '极限弯矩', type: 'bar', data: jointTypes.map(j => j.ultimate_moment / 10000), itemStyle: { color: jointTypes.map(j => CATEGORY_COLORS[j.category]) } },
                  { name: '延性系数', type: 'line', yAxisIndex: 1, data: jointTypes.map(j => +(j.ultimate_rotation / j.yield_rotation).toFixed(1)), lineStyle: { color: '#eb2f96', width: 3 }, symbol: 'diamond', symbolSize: 12 }
                ]
              }}
              style={{ height: 320 }}
            />
          </Card>
        </Col>
      </Row>

      <Divider orientation="left" style={{ marginTop: 24 }}>循环加载力学响应仿真 {running && <Tag color="processing" style={{ marginLeft: 8 }}>计算中...</Tag>}</Divider>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card loading={running}>
            <ReactECharts option={hysteresisOption(simResult)} style={{ height: 380 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card loading={running}>
            <ReactECharts option={backboneOption(simResult)} style={{ height: 380 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 0 }}>
        <Col xs={24} lg={12}>
          <Card title="能量耗散分析" loading={running}>
            {simResult?.energy_dissipation ? (
              <Row gutter={16}>
                <Col span={8}><Card size="small"><Statistic title="总耗散能" value={simResult.energy_dissipation.total_energy?.toFixed(0)} suffix="J" valueStyle={{ fontSize: 16, color: '#D4612B' }} /></Card></Col>
                <Col span={8}><Card size="small"><Statistic title="等效阻尼比" value={(simResult.energy_dissipation.equivalent_damping_ratio * 100).toFixed(2)} suffix="%" valueStyle={{ fontSize: 16, color: '#2B61D4' }} /></Card></Col>
                <Col span={8}><Card size="small"><Statistic title="耗能比" value={(simResult.energy_dissipation.energy_dissipation_ratio).toFixed(1)} suffix="×" valueStyle={{ fontSize: 16, color: '#52c41a' }} /></Card></Col>
              </Row>
            ) : <Empty />}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card loading={running}>
            <ReactECharts option={stiffnessOption(simResult)} style={{ height: 260 }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MortiseTenon;
