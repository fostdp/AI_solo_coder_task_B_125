import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Row, Col, Card, Table, Tag, Typography, Slider, Button, Space,
  Tabs, Divider, Progress, Empty, Spin, Statistic, Alert, Steps
} from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';
import TowerCollapseView, { FLOOR_COLORS } from './TowerCollapseView';

const { Title, Paragraph, Text } = Typography;

export interface CollapseSimulatorProps {
  defaultPga?: number;
  defaultDuration?: number;
}

const CollapseSimulator: React.FC<CollapseSimulatorProps> = ({
  defaultPga = 0.4,
  defaultDuration = 20.0,
}) => {
  const [pga, setPga] = useState(defaultPga);
  const [duration, setDuration] = useState(defaultDuration);
  const [result, setResult] = useState<any>(null);
  const [capResult, setCapResult] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [capRunning, setCapRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const playTimer = useRef<number | null>(null);

  const runSim = async () => {
    setRunning(true);
    setResult(null);
    setCurrentStep(0);
    try {
      const res = await api.post('/new/collapse/run', { earthquake_pga: pga, duration, time_step: 0.02 });
      setResult(res.data.result);
    } finally {
      setRunning(false);
    }
  };

  const runCapacity = async () => {
    setCapRunning(true);
    setCapResult(null);
    try {
      const res = await api.post('/new/collapse/evaluate_capacity', {
        start_pga: 0.1, end_pga: 2.0, pga_step: 0.15
      });
      setCapResult(res.data.result);
    } finally {
      setCapRunning(false);
    }
  };

  useEffect(() => {
    if (playing && result) {
      playTimer.current = window.setInterval(() => {
        setCurrentStep(s => {
          const total = result.time_history?.time_array?.length || 0;
          if (s + 5 >= total) {
            setPlaying(false);
            return total - 1;
          }
          return s + 5;
        });
      }, 30);
    } else if (playTimer.current) {
      clearInterval(playTimer.current);
    }
    return () => { if (playTimer.current) clearInterval(playTimer.current); };
  }, [playing, result]);

  const th = result?.time_history;
  const currentTime = th?.time_array?.[currentStep] || 0;
  const currentDisp = th?.displacement_mm?.[currentStep] || [0, 0, 0, 0, 0];
  const currentDrift = th?.drift_ratios?.[currentStep] || [0, 0, 0, 0, 0];
  const currentDmg = th?.damage_indices?.[currentStep] || [0, 0, 0, 0, 0];
  const collapsedFloors = (result?.failure_sequence || []).filter((f: any) => f.event_type === 'story_collapse_init').reduce((acc: boolean[], f: any) => { const c = [...acc]; c[f.floor - 1] = true; return c; }, [false, false, false, false, false]);

  const dispOption = useMemo(() => {
    if (!th) return {};
    return {
      title: { text: '各楼层位移时程 (mm)', left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      legend: { data: [1, 2, 3, 4, 5].map(i => `第${i}层`), bottom: 0 },
      grid: { left: 60, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: th.time_array, name: '时间 (s)' },
      yAxis: { type: 'value', name: '位移 (mm)' },
      series: [0, 1, 2, 3, 4].map(f => ({
        name: `第${f + 1}层`,
        type: 'line',
        showSymbol: false,
        data: th.displacement_mm.map((row: number[]) => row[f]),
        lineStyle: { color: FLOOR_COLORS[f], width: 1.8 },
        markLine: currentStep ? {
          data: [{ xAxis: th.time_array[currentStep], lineStyle: { color: '#ff4d4f', type: 'dashed' } }]
        } : undefined
      }))
    };
  }, [th, currentStep]);

  const driftOption = useMemo(() => {
    if (!th) return {};
    return {
      title: { text: '各层层间位移角', left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { left: 60, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: th.time_array, name: '时间 (s)' },
      yAxis: { type: 'value', name: '位移角 (1/x)', axisLabel: { formatter: (v: number) => v > 0 ? `1/${Math.round(1/v)}` : '0' } },
      series: [0, 1, 2, 3, 4].map(f => ({
        name: `第${f + 1}层`,
        type: 'line',
        showSymbol: false,
        data: th.drift_ratios.map((row: number[]) => row[f]),
        lineStyle: { color: FLOOR_COLORS[f], width: 1.8 }
      })),
      markLine: { silent: true, data: [{ yAxis: 1 / 40, name: '倒塌阈值 1/40', lineStyle: { color: '#ff4d4f' } }] }
    };
  }, [th]);

  const capacityOption = useMemo(() => {
    if (!capResult?.capacity_curve) return {};
    const cc = capResult.capacity_curve;
    return {
      title: { text: '能力曲线 (Pushover)', left: 'center', textStyle: { fontSize: 13 } },
      tooltip: { trigger: 'axis' },
      legend: { data: ['最大位移角', '最大损伤', '状态点'], bottom: 0 },
      grid: { left: 70, right: 70, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: cc.map((c: any) => `${c.pga.toFixed(2)}g`), name: '地震动峰值加速度' },
      yAxis: [
        { type: 'value', name: '层间位移角', axisLabel: { formatter: (v: number) => v > 0 ? `1/${Math.round(1/Math.max(v,1e-6))}` : '0' } },
        { type: 'value', name: '损伤指数', max: 1.1 }
      ],
      series: [
        {
          name: '最大位移角', type: 'line',
          data: cc.map((c: any) => c.max_drift_ratio),
          lineStyle: { color: '#ff4d4f', width: 3 }, symbol: 'circle', symbolSize: 8,
          markLine: { data: [{ yAxis: 1 / 40, name: '倒塌阈值', lineStyle: { color: '#ff0000' } }] }
        },
        {
          name: '最大损伤', type: 'line', yAxisIndex: 1,
          data: cc.map((c: any) => c.max_damage_index),
          lineStyle: { color: '#1890ff', width: 2, type: 'dashed' }, symbol: 'diamond', symbolSize: 8
        },
        {
          name: '状态', type: 'scatter', yAxisIndex: 1,
          data: cc.map((c: any) => c.status === 'collapsed' ? 1.05 : null),
          symbolSize: 24, itemStyle: { color: '#ff0000' },
          label: { show: true, formatter: '倒塌', fontSize: 11, color: '#fff', fontWeight: 'bold' }
        }
      ]
    };
  }, [capResult]);

  return (
    <div style={{ padding: 0 }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <Card title="仿真参数" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text>地震动峰值加速度 PGA = <Text strong style={{ color: '#ff4d4f' }}>{pga.toFixed(2)}g</Text></Text>
                <Slider min={0.05} max={2.0} step={0.05} value={pga} onChange={setPga} marks={{ 0.1: '0.1g', 0.4: '0.4g', 0.8: '0.8g', 1.6: '1.6g' }} />
              </div>
              <div>
                <Text>持续时间 = {duration.toFixed(0)}s</Text>
                <Slider min={5} max={60} step={5} value={duration} onChange={setDuration} />
              </div>
              <Row>
                <Col span={12}><Button type="primary" block onClick={runSim} loading={running}>单次倒塌模拟</Button></Col>
                <Col span={12}><Button block onClick={runCapacity} loading={capRunning}>Pushover 评估</Button></Col>
              </Row>
              <Divider style={{ margin: '8px 0' }} />
              <Tag color="blue">设计地震 (8度): 0.16g</Tag>
              <Tag color="orange">罕遇地震: 0.4g</Tag>
              <Tag color="red">极罕遇: 0.9g+</Tag>
            </Space>
          </Card>
          {result && (
            <Card title="模拟结果摘要" size="small" style={{ marginTop: 16 }}>
              <Row gutter={[8, 8]}>
                <Col span={12}><Card size="small" style={{ borderTop: '3px solid #ff4d4f' }}><Statistic title="倒塌模式" value={({no_collapse:'未倒塌',near_collapse:'接近倒塌',progressive_collapse:'连续倒塌',lower_floor_collapse:'底层倒塌'} as any)[result.collapse_mode] || result.collapse_mode} valueStyle={{ fontSize: 14 }} /></Card></Col>
                <Col span={12}><Card size="small" style={{ borderTop: '3px solid #faad14' }}><Statistic title="倒塌时间" value={result.collapse_time ? result.collapse_time.toFixed(2) : '-'} suffix={result.collapse_time ? 's' : ''} valueStyle={{ fontSize: 14 }} /></Card></Col>
                <Col span={12}><Card size="small" style={{ borderTop: '3px solid #1890ff' }}><Statistic title="最大层间位移角" value={result.max_drift_ratio > 0 ? `1/${Math.round(1/result.max_drift_ratio)}` : '-'} valueStyle={{ fontSize: 14 }} /></Card></Col>
                <Col span={12}><Card size="small" style={{ borderTop: '3px solid #52c41a' }}><Statistic title="延性系数 μ" value={result.ductility_factor?.toFixed(2)} valueStyle={{ fontSize: 14 }} /></Card></Col>
                <Col span={12}><Card size="small"><Statistic title="超高强系数" value={result.overstrength_factor?.toFixed(2)} valueStyle={{ fontSize: 14 }} /></Card></Col>
                <Col span={12}><Card size="small"><Statistic title="基底剪力峰值" value={result.max_base_shear ? (result.max_base_shear / 1000).toFixed(1) : '-'} suffix={result.max_base_shear ? 'kN' : ''} valueStyle={{ fontSize: 14 }} /></Card></Col>
              </Row>
              {result.collapse_mode === 'no_collapse' && <Alert style={{ marginTop: 8 }} type="success" message={`在 ${pga.toFixed(2)}g 地震作用下，木塔保持稳定，安全裕度充足！`} showIcon />}
              {result.collapse_mode !== 'no_collapse' && <Alert style={{ marginTop: 8 }} type="warning" message={result.collapse_floor ? `第 ${result.collapse_floor} 层发生 ${({progressive_collapse:'连续倒塌',lower_floor_collapse:'局部倒塌'} as any)[result.collapse_mode] || '损伤'}` : '结构严重损伤'} showIcon />}
            </Card>
          )}
          {capResult && (
            <Card title="极限抗震能力" size="small" style={{ marginTop: 16 }}>
              <Steps direction="vertical" size="small" current={4} style={{ marginBottom: 8 }}>
                <Steps.Step title={`正常使用 PGA ≤ ${capResult.performance_levels?.operational_pga?.toFixed(2)}g`} description="结构完好" icon={<Tag color="green">良好</Tag>} />
                <Steps.Step title={`立即可用 PGA ≤ ${capResult.performance_levels?.immediate_occupancy_pga?.toFixed(2)}g`} description="轻微损伤" icon={<Tag color="blue">可接受</Tag>} />
                <Steps.Step title={`生命安全 PGA ≤ ${capResult.performance_levels?.life_safety_pga?.toFixed(2)}g`} description="严重但不倒" icon={<Tag color="orange">临界</Tag>} />
                <Steps.Step title={`防倒塌 PGA ≤ ${capResult.performance_levels?.collapse_prevention_pga?.toFixed(2)}g`} description="接近倒塌" icon={<Tag color="red">危险</Tag>} />
              </Steps>
              <Row gutter={8}>
                <Col span={12}><Card size="small" type="inner"><Statistic title="极限PGA" value={capResult.ultimate_pga?.toFixed(2)} suffix="g" valueStyle={{ color: '#ff4d4f', fontSize: 15 }} /></Card></Col>
                <Col span={12}><Card size="small" type="inner"><Statistic title="设计安全储备" value={capResult.safety_margin_vs_design?.toFixed(1)} suffix="×" valueStyle={{ color: '#52c41a', fontSize: 15 }} /></Card></Col>
              </Row>
            </Card>
          )}
        </Col>

        <Col xs={24} lg={10}>
          <Card
            title={<Space><Text strong>倒塌过程可视化</Text>{playing ? <Tag color="processing">播放中 {currentStep}/{th?.time_array?.length || 0}</Tag> : null}</Space>}
            extra={result && (
              <Space>
                <Button size="small" onClick={() => setPlaying(!playing)}>{playing ? '⏸ 暂停' : '▶ 播放'}</Button>
                <Button size="small" onClick={() => setCurrentStep(0)}>⏮ 复位</Button>
                <Text type="secondary">t = {currentTime.toFixed(2)}s</Text>
              </Space>
            )}
          >
            {running ? (
              <div style={{ textAlign: 'center', padding: 120 }}><Spin size="large" tip="正在计算倒塌响应..." /></div>
            ) : result ? (
              <>
                <TowerCollapseView
                  floorCount={5}
                  floorHeights={[6.59, 5.49, 4.99, 4.59, 4.09]}
                  floorDiameters={[30.27, 22.65, 18.46, 15.28, 12.10]}
                  displacements={currentDisp}
                  damageIndices={currentDmg}
                  collapsedFloors={collapsedFloors}
                  failureSequence={result.failure_sequence || []}
                  currentTime={currentTime}
                />
                <Divider style={{ margin: '8px 0' }} />
                <Text style={{ fontSize: 12 }}>各楼层状态（当前时刻）：</Text>
                <Row gutter={[8, 8]}>
                  {[0, 1, 2, 3, 4].map(f => (
                    <Col key={f} span={Math.floor(24 / 5)}>
                      <Card size="small" style={{ background: collapsedFloors[f] ? '#fff1f0' : 'transparent' }}>
                        <Text strong style={{ color: FLOOR_COLORS[f] }}>{f + 1}F</Text>
                        <div style={{ fontSize: 11 }}>
                          Δ={(currentDrift[f] * 100).toFixed(2)}%<br />
                          D={(currentDmg[f] * 100).toFixed(0)}%
                        </div>
                        <Progress percent={Math.round(currentDmg[f] * 100)} size="small"
                                  strokeColor={FLOOR_COLORS[f]} showInfo={false} style={{ marginTop: 2 }} />
                      </Card>
                    </Col>
                  ))}
                </Row>
              </>
            ) : (
              <Empty description="请点击左侧“单次倒塌模拟”开始" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={7}>
          <Card title="仿真结果图表" size="small">
            <Tabs size="small"
                  items={[
                    {
                      key: 'disp', label: '位移时程',
                      children: result ? <ReactECharts option={dispOption} style={{ height: 340 }} /> : <Empty />
                    },
                    {
                      key: 'drift', label: '层间位移角',
                      children: result ? <ReactECharts option={driftOption} style={{ height: 340 }} /> : <Empty />
                    },
                    {
                      key: 'capacity', label: 'Pushover曲线',
                      children: capResult ? <ReactECharts option={capacityOption} style={{ height: 340 }} /> : <Empty description="请点击“Pushover 评估”" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    },
                    {
                      key: 'events', label: '失效序列',
                      children: result?.failure_sequence?.length ? (
                        <Table size="small" pagination={false}
                               dataSource={(result.failure_sequence || []).map((e: any, i: number) => ({ ...e, key: i }))}
                               columns={[
                                 { title: '时间(s)', dataIndex: 'time', render: (v: number) => v.toFixed(2), width: 70 },
                                 { title: '楼层', dataIndex: 'floor', width: 50 },
                                 { title: '位移角', dataIndex: 'drift_ratio', render: (v: number) => `1/${Math.round(1 / Math.max(v, 1e-6))}`, width: 80 },
                                 { title: '事件', dataIndex: 'event_type', render: (v: string) => <Tag color={v.includes('collapse') ? 'red' : 'orange'}>{({story_collapse_init:'倒塌开始',severe_damage:'严重损伤'} as any)[v] || v}</Tag> }
                               ]} />
                      ) : <Empty />
                    }
                  ]} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CollapseSimulator;
