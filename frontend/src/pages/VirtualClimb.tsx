import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  Row, Col, Card, Tag, Typography, Slider, Button, Space, Divider, Progress,
  Spin, Alert, Steps, Statistic, Descriptions, InputNumber, Tour, Result, Badge
} from 'antd';
import api from '../services/api';

const { Title, Paragraph, Text } = Typography;

interface VirtualState {
  session: any;
  position: { x: number; y: number; z: number; floor: number; waypoint_name: string; progress: number };
  wind_response: any;
  sensory_data: any;
  floor_info: any;
}

const VirtualClimb: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [session, setSession] = useState<any>(null);
  const [state, setState] = useState<VirtualState | null>(null);
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [windSpeed, setWindSpeed] = useState(5.0);
  const [earthquakePga, setEarthquakePga] = useState(0.0);
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const timerRef = useRef<number | null>(null);
  const sceneRef = useRef<any>(null);

  const FLOOR_NAMES = ['台基入口', '一层佛殿', '二层平座', '三层暗层', '四层佛殿', '五层明层', '塔刹观景区'];
  const WAYPOINT_NAMES = ['入口', '台基', '一层内槽', '二层平座', '三层暗层', '四层佛殿', '五层明层', '塔刹'];

  const startSession = async () => {
    setLoading(true);
    try {
      const res = await api.post('/new/virtual/start');
      setSession(res.data.session);
      setTimeElapsed(0);
    } finally {
      setLoading(false);
    }
  };

  const updateState = async (t: number, ws: number, pga: number) => {
    if (!session) return;
    try {
      const res = await api.post('/new/virtual/update', {
        session_id: session.session_id,
        time_elapsed: t,
        wind_speed: ws,
        earthquake_pga: pga
      });
      setState(res.data.state);
    } catch {}
  };

  useEffect(() => {
    if (!session) return;
    if (playing && autoAdvance) {
      timerRef.current = window.setInterval(() => {
        setTimeElapsed(t => Math.min(t + 1, session.total_duration || 600));
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [playing, autoAdvance, session]);

  useEffect(() => {
    if (session) updateState(timeElapsed, windSpeed, earthquakePga);
  }, [session, timeElapsed, windSpeed, earthquakePga]);

  useEffect(() => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const W = canvas.width;
    const H = canvas.height;

    let t = 0;
    const animate = () => {
      t += 0.016;
      ctx.clearRect(0, 0, W, H);
      const skyGrad = ctx.createLinearGradient(0, 0, 0, H);
      skyGrad.addColorStop(0, '#87CEEB');
      skyGrad.addColorStop(0.6, '#E0F6FF');
      skyGrad.addColorStop(1, '#F5EFE6');
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = '#fff';
      for (let i = 0; i < 8; i++) {
        const cx = (i * 110 + t * 5) % (W + 100) - 50;
        const cy = 50 + (i % 3) * 40;
        ctx.globalAlpha = 0.75;
        ctx.beginPath();
        ctx.arc(cx, cy, 22, 0, Math.PI * 2);
        ctx.arc(cx + 20, cy + 4, 18, 0, Math.PI * 2);
        ctx.arc(cx + 36, cy, 15, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      const currY = state?.position?.y || 0;
      const maxY = 32;
      const camY = Math.min(currY, 28);
      const baseScale = 220 / maxY;
      const floorHeights = [0, 6.59, 5.49, 4.99, 4.59, 4.09];
      const floorDiams = [30.27, 30.27, 22.65, 18.46, 15.28, 12.10];
      const dispX = state?.wind_response?.displacement_x_mm || 0;
      const dispY = state?.wind_response?.displacement_y_mm || 0;
      const windOffsetX = Math.sin(t * (state?.wind_response?.acceleration_x || 0.1) * 8) * Math.min(8, dispX * 0.08);
      const windOffsetY = Math.cos(t * (state?.wind_response?.acceleration_y || 0.08) * 10) * Math.min(6, dispY * 0.1);

      let cumH = 0;
      for (let f = 0; f < 5; f++) {
        const floorTop = (cumH + floorHeights[f + 1]) * baseScale;
        const floorBottom = cumH * baseScale;
        const d = floorDiams[f + 1] * 5.5;
        const left = W / 2 - d / 2 + windOffsetX * (f + 1) / 5;
        const top = H - floorTop - 40 - camY * 5;
        const h = floorHeights[f + 1] * baseScale;
        const grad = ctx.createLinearGradient(left, top, left + d, top);
        grad.addColorStop(0, '#8B4513');
        grad.addColorStop(0.5, '#CD853F');
        grad.addColorStop(1, '#8B4513');
        ctx.fillStyle = grad;
        ctx.fillRect(left, top, d, h);
        ctx.fillStyle = '#A0522D';
        for (let c = 0; c < 8; c++) {
          const cx = left + 8 + c * ((d - 16) / 7);
          ctx.fillRect(cx, top + 4, 3, h - 8);
        }
        ctx.fillStyle = '#8B0000';
        ctx.beginPath();
        const roofW = d * 1.22;
        const roofL = W / 2 - roofW / 2 + windOffsetX * (f + 1) / 5;
        ctx.moveTo(roofL - 8, top + 6);
        ctx.lineTo(W / 2, top - 18);
        ctx.lineTo(roofL + roofW + 8, top + 6);
        ctx.closePath();
        ctx.fill();
        cumH += floorHeights[f + 1];
      }
      const d5 = floorDiams[5] * 5.5;
      const topSpireY = H - cumH * baseScale - 40 - camY * 5;
      ctx.fillStyle = '#B8860B';
      ctx.beginPath();
      ctx.moveTo(W / 2 - d5 * 0.3, topSpireY);
      ctx.lineTo(W / 2, topSpireY - 55);
      ctx.lineTo(W / 2 + d5 * 0.3, topSpireY);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#FFD700';
      ctx.fillRect(W / 2 - 2, topSpireY - 75, 4, 25);

      ctx.fillStyle = '#766458';
      ctx.fillRect(0, H - 40, W, 40);
      ctx.fillStyle = '#555';
      for (let i = 0; i < W; i += 28) {
        ctx.fillRect(i, H - 36, 18, 3);
      }

      const viewerX = W / 2 + Math.sin(t * 0.2 + windOffsetX * 0.02) * 4;
      const viewerYBottom = H - 40 - (camY * 5);
      ctx.fillStyle = 'rgba(0,0,0,0.1)';
      ctx.beginPath();
      ctx.ellipse(viewerX, viewerYBottom + 2, 14, 4, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(W / 2, H - 60);
      ctx.lineTo(W / 2, viewerYBottom - 5);
      ctx.stroke();
      ctx.setLineDash([]);

      if (windSpeed > 10 || earthquakePga > 0) {
        ctx.strokeStyle = `rgba(180,180,255,${Math.min(0.7, windSpeed / 30 + earthquakePga)})`;
        for (let i = 0; i < Math.min(25, 5 + Math.floor(windSpeed / 3) + earthquakePga * 30); i++) {
          const wx = (t * (150 + windSpeed * 5) + i * 80) % (W + 50) - 25;
          const wy = 80 + ((i * 37 + t * 60) % (H - 150));
          ctx.beginPath();
          ctx.moveTo(wx, wy);
          ctx.lineTo(wx + 15 + windSpeed, wy + 2);
          ctx.lineWidth = 1 + Math.random();
          ctx.stroke();
        }
        if (earthquakePga > 0) {
          ctx.fillStyle = `rgba(255,0,0,${Math.min(0.3, earthquakePga)})`;
          ctx.fillRect(0, 0, W, H);
        }
      }

      ctx.fillStyle = '#fff';
      ctx.fillRect(10, 10, 210, 90);
      ctx.strokeStyle = '#333';
      ctx.strokeRect(10, 10, 210, 90);
      ctx.fillStyle = '#333';
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText(`📍 当前位置: ${state?.position?.waypoint_name || '入口'}`, 20, 28);
      ctx.font = '11px sans-serif';
      ctx.fillText(`🏛 楼层: ${state?.position?.floor ? ('第 ' + state.position.floor + ' 层') : '台基'}`, 20, 44);
      ctx.fillText(`📐 高度: ${(state?.position?.y || 0).toFixed(1)} m`, 20, 60);
      ctx.fillText(`💨 风速: ${windSpeed.toFixed(1)} m/s`, 20, 76);
      ctx.fillText(`🌪 体感: ${state?.wind_response?.comfort_level || '无感'}`, 20, 92);

      requestAnimationFrame(animate);
    };
    const id = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(id);
  }, [state, windSpeed, earthquakePga]);

  const totalDuration = session?.total_duration || 600;
  const progress = totalDuration ? (timeElapsed / totalDuration) * 100 : 0;
  const currentWaypointIdx = Math.min(7, Math.max(0, Math.floor((progress / 100) * 7)));

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        公众虚拟登塔体验
        <Tag color="purple" style={{ marginLeft: 12 }}>第一人称 · 风振体感</Tag>
        <Button style={{ marginLeft: 8 }} size="small" onClick={() => setTourOpen(true)}>使用向导</Button>
      </Title>
      <Paragraph type="secondary">沉浸式体验攀登应县木塔的完整过程，感受不同高度的风振响应、建筑空间序列与文化艺术之美</Paragraph>

      {!session ? (
        <Card style={{ textAlign: 'center', padding: 40 }}>
          <Result
            status="info"
            title="准备开始虚拟登塔之旅"
            subTitle="全程约10分钟，沿途经过8个景观节点，可实时调节风速感受不同风振体验"
            extra={
              <Space>
                <Button type="primary" size="large" onClick={startSession} loading={loading}>开始登塔</Button>
                <Button size="large" onClick={() => setWindSpeed(25)}>预设大风场景</Button>
              </Space>
            }
          />
        </Card>
      ) : (
        <>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={[12, 12]} align="middle">
              <Col xs={24} md={14}>
                <Steps current={currentWaypointIdx} size="small"
                       items={WAYPOINT_NAMES.map(n => ({ title: n }))} />
                <Progress percent={progress} showInfo style={{ marginTop: 10 }} strokeColor={{ '0%': '#52c41a', '50%': '#1890ff', '100%': '#722ed1' }} />
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  进度: <Text strong>{timeElapsed}s</Text> / {totalDuration}s · 已游览 <Text strong>{WAYPOINT_NAMES[currentWaypointIdx]}</Text>
                </div>
              </Col>
              <Col xs={24} md={10}>
                <Space wrap>
                  <Button.Group>
                    <Button type={playing ? 'default' : 'primary'} onClick={() => setPlaying(true)} disabled={timeElapsed >= totalDuration}>▶ 自动攀登</Button>
                    <Button onClick={() => setPlaying(false)}>⏸ 暂停</Button>
                    <Button onClick={() => { setTimeElapsed(0); setPlaying(false); }}>⏮ 重置</Button>
                  </Button.Group>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <Text style={{ fontSize: 12 }}>跳跃到</Text>
                    <InputNumber size="small" min={0} max={totalDuration} value={timeElapsed}
                                 onChange={v => setTimeElapsed(Number(v) || 0)} />
                    <Text style={{ fontSize: 12 }}>秒</Text>
                  </div>
                </Space>
              </Col>
            </Row>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={14}>
              <Card
                title={<Space>
                  <Tag color="purple">第一人称视角</Tag>
                  <Text>风振位移 {((state?.wind_response?.displacement_x_mm || 0) + (state?.wind_response?.displacement_y_mm || 0) / 2).toFixed(1)} mm</Text>
                </Space>}
                extra={
                  <Badge status={state?.wind_response?.comfort_level === '难以忍受' ? 'error'
                    : state?.wind_response?.comfort_level === '不适' ? 'warning'
                    : state?.wind_response?.comfort_level === '有感' ? 'processing' : 'success'}
                         text={state?.wind_response?.comfort_level || '体感舒适'} />
                }
                bodyStyle={{ padding: 0 }}
              >
                <canvas ref={canvasRef} width={800} height={520}
                        style={{ width: '100%', height: 'auto', display: 'block', borderRadius: '0 0 8px 8px' }} />
                <Tour
                  open={tourOpen}
                  onClose={() => setTourOpen(false)}
                  steps={[
                    { title: '虚拟场景', description: 'Canvas 实时渲染的登塔场景，动态展示风速与塔体摆动', target: canvasRef.current as any },
                    { title: '风速控制', description: '右侧滑块调节风速，15m/s以上有明显体感', placement: 'left' },
                    { title: '建筑介绍', description: '每个楼层的建筑、佛像、景观解说卡片', placement: 'left' }
                  ]}
                />
              </Card>
              {state?.wind_response && (
                <Alert
                  style={{ marginTop: 12 }}
                  type={state.wind_response.comfort_level === '难以忍受' ? 'error'
                    : state.wind_response.comfort_level === '不适' ? 'warning'
                    : state.wind_response.comfort_level === '有感' ? 'info' : 'success'}
                  showIcon
                  message={
                    <Space direction="vertical" size={0}>
                      <Text strong>风振体感：{state.wind_response.comfort_level}</Text>
                      <Text style={{ fontSize: 13 }}>{state.wind_response.perception_description || ''}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        塔顶位移 {state.wind_response.displacement_x_mm?.toFixed(2)}mm(X) + {state.wind_response.displacement_y_mm?.toFixed(2)}mm(Y) · 
                        加速度 {(state.wind_response.acceleration_x + state.wind_response.acceleration_y / 2).toFixed(4)} m/s²
                      </Text>
                    </Space>
                  }
                />
              )}
            </Col>

            <Col xs={24} lg={10}>
              <Card title="环境参数" size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Row justify="space-between">
                      <Text>💨 风速</Text>
                      <Text strong style={{ color: windSpeed > 15 ? '#fa8c16' : windSpeed > 8 ? '#1890ff' : '#52c41a' }}>{windSpeed.toFixed(1)} m/s</Text>
                    </Row>
                    <Slider min={0} max={50} step={0.5} value={windSpeed} onChange={setWindSpeed}
                            marks={{ 0: '静风', 8: '微风', 15: '中强风', 25: '大风', 40: '强风' }} />
                  </div>
                  <div>
                    <Row justify="space-between">
                      <Text>🌋 模拟地震 PGA</Text>
                      <Text strong style={{ color: earthquakePga > 0.3 ? '#ff4d4f' : earthquakePga > 0.1 ? '#faad14' : '#333' }}>{earthquakePga.toFixed(2)}g</Text>
                    </Row>
                    <Slider min={0} max={1.0} step={0.02} value={earthquakePga} onChange={setEarthquakePga}
                            marks={{ 0: '无', 0.16: '8度', 0.4: '罕遇', 0.9: '极罕' }} />
                  </div>
                </Space>
              </Card>

              {state?.sensory_data && (
                <Card title="多模态体感反馈" size="small" style={{ marginTop: 16 }}>
                  <Space direction="vertical" style={{ width: '100%' }} size={6}>
                    <Row gutter={6}>
                      <Col span={12}>
                        <Card size="small" type="inner" style={{ borderTop: '3px solid #1890ff' }}>
                          <Statistic title="👁 视觉" value={state.sensory_data.visual?.sway_amplitude_mm?.toFixed?.(1) || 0} suffix="mm" valueStyle={{ fontSize: 14 }} />
                          <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{state.sensory_data.visual?.description || ''}</div>
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card size="small" type="inner" style={{ borderTop: '3px solid #722ed1' }}>
                          <Statistic title="👂 听觉" value={state.sensory_data.auditory?.wind_noise_db?.toFixed?.(0) || 30} suffix="dB" valueStyle={{ fontSize: 14 }} />
                          <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>{state.sensory_data.auditory?.description || ''}</div>
                        </Card>
                      </Col>
                    </Row>
                    <Row gutter={6}>
                      <Col span={12}>
                        <Card size="small" type="inner" style={{ borderTop: '3px solid #52c41a' }}>
                          <Statistic title="✋ 触觉" value={state.sensory_data.tactile?.vibration_level || 0} prefix="Lv" valueStyle={{ fontSize: 14 }} />
                          <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                            T:{state.sensory_data.tactile?.temperature?.toFixed?.(0) || 20}°C · 
                            RH:{state.sensory_data.tactile?.humidity?.toFixed?.(0) || 50}%
                          </div>
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card size="small" type="inner" style={{ borderTop: '3px solid #fa8c16' }}>
                          <Statistic title="🏃 本体感" value={state.sensory_data.kinesthetic?.floor_tilt_degrees?.toFixed?.(2) || 0} suffix="°" valueStyle={{ fontSize: 14 }} />
                          <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                            坡度 {state.sensory_data.kinesthetic?.stair_slope?.toFixed?.(0) || 0}°
                          </div>
                        </Card>
                      </Col>
                    </Row>
                  </Space>
                </Card>
              )}

              {state?.floor_info && (
                <Card
                  title={<><Tag color="gold">建筑文化</Tag> {state.floor_info.name}</>}
                  size="small"
                  style={{ marginTop: 16 }}
                >
                  <Descriptions size="small" column={1}>
                    <Descriptions.Item label="建筑特色">{state.floor_info.architecture_features}</Descriptions.Item>
                    <Descriptions.Item label="佛像/文物">{state.floor_info.buddha_info}</Descriptions.Item>
                    <Descriptions.Item label="观景描述">{state.floor_info.view_description}</Descriptions.Item>
                  </Descriptions>
                </Card>
              )}
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default VirtualClimb;
