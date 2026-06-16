import React, { useState, useEffect, useRef } from 'react';
import {
  Row, Col, Card, Table, Tag, Typography, Space, Divider, Progress,
  Descriptions, Empty, Spin, Alert
} from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';

const { Title, Paragraph, Text } = Typography;

interface PagodaInfo {
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

const PagodaMiniModel: React.FC<{ info: PagodaInfo; color: string }> = ({ info, color }) => {
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

const DynastyCompare: React.FC = () => {
  const [pagodaA, setPagodaA] = useState<PagodaInfo | null>(null);
  const [pagodaB, setPagodaB] = useState<PagodaInfo | null>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [windSpeed, setWindSpeed] = useState(25);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [a, b, r] = await Promise.all([
          api.get('/new/dynasty/pagoda/yingxian'),
          api.get('/new/dynasty/pagoda/gojunoto'),
          api.get('/new/dynasty/compare', { params: { a: 'yingxian', b: 'gojunoto' } })
        ]);
        setPagodaA(a.data);
        setPagodaB(b.data);
        setReport(r.data.report);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const frequencyOption = (a: PagodaInfo | null, b: PagodaInfo | null, rep: any) => {
    if (!rep?.natural_frequency_comparison) return {};
    const fc = rep.natural_frequency_comparison;
    return {
      title: { text: '前5阶固有频率对比 (Hz)', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { data: [a?.name || 'A', b?.name || 'B'], bottom: 0 },
      grid: { left: 50, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: ['第1阶', '第2阶', '第3阶', '第4阶', '第5阶'] },
      yAxis: { type: 'value', name: '频率 (Hz)' },
      series: [
        { name: a?.name || 'A', type: 'bar', data: fc.frequencies_a || [], itemStyle: { color: '#D4612B' } },
        { name: b?.name || 'B', type: 'bar', data: fc.frequencies_b || [], itemStyle: { color: '#2B61D4' } }
      ]
    };
  };

  const structureOption = (a: PagodaInfo | null, b: PagodaInfo | null) => {
    if (!a || !b) return {};
    return {
      title: { text: '各层直径与高度对比', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { left: 50, right: 30, top: 40, bottom: 50 },
      xAxis: { type: 'category', data: a.floor_heights.map((_, i) => `第${i + 1}层`) },
      yAxis: [
        { type: 'value', name: '直径 (m)' },
        { type: 'value', name: '层高 (m)' }
      ],
      series: [
        { name: `${a.name} 直径`, type: 'line', data: a.floor_diameters, itemStyle: { color: '#D4612B' } },
        { name: `${b.name} 直径`, type: 'line', data: b.floor_diameters, itemStyle: { color: '#2B61D4' } },
        { name: `${a.name} 层高`, type: 'bar', yAxisIndex: 1, data: a.floor_heights, itemStyle: { color: '#F4A261', opacity: 0.5 } },
        { name: `${b.name} 层高`, type: 'bar', yAxisIndex: 1, data: b.floor_heights, itemStyle: { color: '#618FF4', opacity: 0.5 } }
      ]
    };
  };

  const materialOption = (a: PagodaInfo | null, b: PagodaInfo | null) => {
    if (!a || !b) return {};
    return {
      title: { text: '木材力学参数对比 (对数尺度)', left: 'center', textStyle: { fontSize: 14 } },
      tooltip: {},
      radar: {
        indicator: [
          { name: '顺纹E', max: 12000 },
          { name: '径向E', max: 1000 },
          { name: '弦向E', max: 600 },
          { name: '密度', max: 600 },
          { name: '节点刚度', max: 1.5e8 }
        ],
        scale: true
      },
      series: [{
        type: 'radar',
        data: [
          { name: a.name, value: [a.timber_properties.E_L, a.timber_properties.E_R, a.timber_properties.E_T, a.timber_properties.density, a.joint_properties.rotational_stiffness], areaStyle: { opacity: 0.2 }, itemStyle: { color: '#D4612B' } },
          { name: b.name, value: [b.timber_properties.E_L, b.timber_properties.E_R, b.timber_properties.E_T, b.timber_properties.density, b.joint_properties.rotational_stiffness], areaStyle: { opacity: 0.2 }, itemStyle: { color: '#2B61D4' } }
        ]
      }]
    };
  };

  if (loading) return <div style={{ padding: 60, textAlign: 'center' }}><Spin size="large" tip="加载对比数据..." /></div>;

  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        中日木塔结构设计对比
        <Tag color="geekblue" style={{ marginLeft: 12 }}>应县木塔 vs 法隆寺五重塔</Tag>
      </Title>
      <Paragraph type="secondary">从建筑形制、结构体系、抗震理念三个维度对比中、日两国古代木塔的设计智慧差异</Paragraph>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card>
            <PagodaMiniModel info={pagodaA!} color="#D4612B" />
            <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
              <Descriptions.Item label="朝代">{pagodaA?.dynasty}</Descriptions.Item>
              <Descriptions.Item label="总高">{pagodaA?.height} m</Descriptions.Item>
              <Descriptions.Item label="层数">{pagodaA?.floor_count}</Descriptions.Item>
              <Descriptions.Item label="结构">楼阁式双筒</Descriptions.Item>
            </Descriptions>
            <Alert type="info" message={<Text strong style={{ color: '#D4612B' }}>抗震理念：{pagodaA?.seismic_philosophy}</Text>} showIcon style={{ marginTop: 8 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <PagodaMiniModel info={pagodaB!} color="#2B61D4" />
            <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
              <Descriptions.Item label="朝代">{pagodaB?.dynasty}</Descriptions.Item>
              <Descriptions.Item label="总高">{pagodaB?.height} m</Descriptions.Item>
              <Descriptions.Item label="层数">{pagodaB?.floor_count}</Descriptions.Item>
              <Descriptions.Item label="结构">心柱独立框架</Descriptions.Item>
            </Descriptions>
            <Alert type="info" message={<Text strong style={{ color: '#2B61D4' }}>抗震理念：{pagodaB?.seismic_philosophy}</Text>} showIcon style={{ marginTop: 8 }} />
          </Card>
        </Col>
      </Row>

      <Divider orientation="left">抗震理念深度对比</Divider>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card size="small" title={<Text strong>中国·以柔克刚</Text>} type="inner" style={{ borderTop: '3px solid #D4612B' }}>
              <Paragraph style={{ fontSize: 13 }}>
                内外双筒结构体系，24根立柱形成坚固外环。榫卯节点半刚性连接，
                允许层间适度滑移变形吸收地震能量。<Text strong>暗层斜撑</Text>如同隐形"加强筋"，
                整体抗扭刚度大。层间刚度均匀递变，避免应力集中。
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title={<Text strong>日本·柔性屈服</Text>} type="inner" style={{ borderTop: '3px solid #2B61D4' }}>
              <Paragraph style={{ fontSize: 13 }}>
                <Text strong>心柱（Shinbashira）</Text>贯穿全塔如同"定海神针"，但不承重、仅提供恢复力。
                各层为独立框架，层间通过"贯抜構法"（贯穿木构件）连接。
                允许层间大错位，以变形换取能量耗散。
              </Paragraph>
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" title={<Text strong>核心差异</Text>} type="inner" style={{ borderTop: '3px solid #52c41a' }}>
              <Paragraph style={{ fontSize: 13 }}>
                {report?.seismic_philosophy_comparison?.differences?.map((d: string, i: number) => (
                  <Text key={i}>✦ {d}<br /></Text>
                )) || (
                  <>
                    <Text>✦ 中国重"整体刚"，日本重"局部柔"<br /></Text>
                    <Text>✦ 节点耗能 vs 层间错位耗能<br /></Text>
                    <Text>✦ 大尺度宏大 vs 小尺度精巧</Text>
                  </>
                )}
              </Paragraph>
            </Card>
          </Col>
        </Row>
      </Card>

      <Divider orientation="left">结构参数与动力特性对比</Divider>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={structureOption(pagodaA, pagodaB)} style={{ height: 360 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={frequencyOption(pagodaA, pagodaB, report)} style={{ height: 360 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 0 }}>
        <Col xs={24} lg={12}>
          <Card>
            <ReactECharts option={materialOption(pagodaA, pagodaB)} style={{ height: 360 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="关键参数对比表">
            <Table
              size="small"
              pagination={false}
              dataSource={[
                { k: '总高度(m)', a: pagodaA?.height, b: pagodaB?.height },
                { k: '首层直径(m)', a: pagodaA?.floor_diameters[0], b: pagodaB?.floor_diameters[0] },
                { k: '高宽比', a: (pagodaA?.height! / pagodaA?.floor_diameters![0]).toFixed(2), b: (pagodaB?.height! / pagodaB?.floor_diameters![0]).toFixed(2) },
                { k: '体积(m³)', a: Math.round(2000), b: Math.round(450) },
                { k: '第一频率(Hz)', a: report?.natural_frequency_comparison?.frequencies_a?.[0]?.toFixed(3), b: report?.natural_frequency_comparison?.frequencies_b?.[0]?.toFixed(3) },
                { k: '顶层风振位移(mm，25m/s)', a: report?.wind_displacement_comparison?.top_disp_a_mm, b: report?.wind_displacement_comparison?.top_disp_b_mm },
                { k: '相对层间刚度', a: '均匀递变', b: '下强上弱' }
              ]}
              columns={[
                { title: '参数', dataIndex: 'k', key: 'k', width: '35%' },
                { title: pagodaA?.name || 'A', dataIndex: 'a', key: 'a', render: (v: any) => <Text strong style={{ color: '#D4612B' }}>{v ?? '-'}</Text> },
                { title: pagodaB?.name || 'B', dataIndex: 'b', key: 'b', render: (v: any) => <Text strong style={{ color: '#2B61D4' }}>{v ?? '-'}</Text> }
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DynastyCompare;
