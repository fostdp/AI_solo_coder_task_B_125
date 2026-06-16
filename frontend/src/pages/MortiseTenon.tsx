import React from 'react';
import { Tag, Typography } from 'antd';
import JoinerySimulator from '../components/JoinerySimulator';

const { Title, Paragraph } = Typography;

const MortiseTenon: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        古代匠人榫卯工艺数字化复原
        <Tag color="gold" style={{ marginLeft: 12 }}>6 类经典榫卯</Tag>
      </Title>
      <Paragraph type="secondary">通过非线性弹簧模型真实还原各类榫卯节点的弯矩-转角滞回特性，支持捏缩效应、刚度退化、能量耗散分析</Paragraph>

      <JoinerySimulator defaultJointId="straight_tenon" />
    </div>
  );
};

export default MortiseTenon;
