import React from 'react';
import { Tag, Typography } from 'antd';
import CollapseSimulator from '../components/CollapseSimulator';

const { Title, Paragraph } = Typography;

const CollapseSimulation: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        木塔地震倒塌模拟与极限抗震评估
        <Tag color="red" style={{ marginLeft: 12 }}>极限状态分析</Tag>
      </Title>
      <Paragraph type="secondary">基于非线性时程分析，模拟木塔在极端地震作用下从屈服、损伤发展到倒塌的完整过程；Pushover评估极限抗震能力储备</Paragraph>

      <CollapseSimulator defaultPga={0.4} defaultDuration={20.0} />
    </div>
  );
};

export default CollapseSimulation;
