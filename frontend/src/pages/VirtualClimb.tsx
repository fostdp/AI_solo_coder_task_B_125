import React from 'react';
import { Tag, Typography, Button } from 'antd';
import VRPagodaExperience from '../components/VRPagodaExperience';

const { Title, Paragraph } = Typography;

const VirtualClimb: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        公众虚拟登塔体验
        <Tag color="purple" style={{ marginLeft: 12 }}>第一人称 · 风振体感</Tag>
        <Button style={{ marginLeft: 8 }} size="small">使用向导</Button>
      </Title>
      <Paragraph type="secondary">沉浸式体验攀登应县木塔的完整过程，感受不同高度的风振响应、建筑空间序列与文化艺术之美</Paragraph>

      <VRPagodaExperience defaultWindSpeed={5.0} />
    </div>
  );
};

export default VirtualClimb;
