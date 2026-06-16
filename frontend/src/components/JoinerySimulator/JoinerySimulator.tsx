import React, { useState, useEffect, useMemo } from 'react';
import {
  Row, Col, Card, Tag, Typography, Slider, Space,
  Divider, Spin, Statistic, Descriptions
} from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';
import Joint3DModel, { JointType, CATEGORY_COLORS, CATEGORY_NAMES } from './Joint3DModel';

const { Title, Text } = Typography;

export interface JoinerySimulatorProps {
  defaultJointId?: string;
}

const JoinerySimulator: React.FC<JoinerySimulatorProps> = ({
  defaultJointId = 'straight_tenon',
}) => {
  const [jointTypes, setJointTypes] = useState<JointType[]>([]);
  const [selectedId, setSelectedId] = useState<string>(defaultJointId);
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
    <div style={{ padding: 0 }}>
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
                      <Statistic value={Math.round(j.damping_ratio * 1000)} valueStyle={{ fontSize: 12, color: CATEGORY_COLORS[j.category] }} />
                      <div style={{ fontSize: 10, color: '#999' }}>阻尼‰</div>
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
            ) : <div style={{ padding: 20, textAlign: 'center', color: '#999' }}>暂无数据</div>}
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

export default JoinerySimulator;
