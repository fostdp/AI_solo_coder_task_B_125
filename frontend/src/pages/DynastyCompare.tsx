import React from 'react';
import { Tag, Typography } from 'antd';
import DesignComparator from '../components/DesignComparator';

const { Title, Paragraph } = Typography;

const DynastyCompare: React.FC = () => {
  return (
    <div style={{ padding: 24 }}>
      <Title level={3} style={{ marginBottom: 4 }}>
        中日木塔结构设计对比
        <Tag color="geekblue" style={{ marginLeft: 12 }}>应县木塔 vs 法隆寺五重塔</Tag>
      </Title>
      <Paragraph type="secondary">从建筑形制、结构体系、抗震理念三个维度对比中、日两国古代木塔的设计智慧差异</Paragraph>

      <DesignComparator defaultPagodaA="yingxian" defaultPagodaB="gojunoto" />
    </div>
  );
};

export default DynastyCompare;
