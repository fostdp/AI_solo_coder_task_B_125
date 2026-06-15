-- ============================================
-- TimescaleDB 降采样与保留策略
-- ============================================

-- 原始数据: 保留90天
SELECT add_retention_policy('sensor_data', INTERVAL '90 days', if_not_exists => TRUE);

-- 10分钟聚合视图: 保留1年
SELECT add_retention_policy('sensor_data_10m', INTERVAL '365 days', if_not_exists => TRUE);

-- 1小时聚合视图: 保留5年
SELECT add_retention_policy('sensor_data_1h', INTERVAL '1825 days', if_not_exists => TRUE);

-- ============================================
-- 1天聚合视图 (从1小时聚合嵌套)
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_1d
WITH (timescaledb.continuous) AS
SELECT
    sensor_id,
    time_bucket('1 day', bucket) AS bucket,
    AVG(avg_value) AS avg_value,
    MIN(min_value) AS min_value,
    MAX(max_value) AS max_value,
    AVG(std_value) AS std_value,
    SUM(sample_count) AS sample_count
FROM sensor_data_1h
GROUP BY sensor_id, time_bucket('1 day', bucket)
WITH NO DATA;

ALTER MATERIALIZED VIEW sensor_data_1d SET (timescaledb.materialized_only = false);

-- 1天聚合视图: 永久保留
SELECT add_retention_policy('sensor_data_1d', INTERVAL '3650 days', if_not_exists => TRUE);

-- ============================================
-- 告警数据: 保留2年
-- ============================================
SELECT add_retention_policy('alerts', INTERVAL '730 days', if_not_exists => TRUE);

-- ============================================
-- 模态参数: 保留5年
-- ============================================
SELECT add_retention_policy('modal_parameters', INTERVAL '1825 days', if_not_exists => TRUE);

-- ============================================
-- 连续聚合刷新策略
-- ============================================

-- 10分钟聚合: 每5分钟刷新
SELECT add_continuous_aggregate_policy('sensor_data_10m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE);

-- 1小时聚合: 每15分钟刷新
SELECT add_continuous_aggregate_policy('sensor_data_1h',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE);

-- 1天聚合: 每1小时刷新
SELECT add_continuous_aggregate_policy('sensor_data_1d',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- ============================================
-- 压缩策略 (7天后的数据启用压缩)
-- ============================================
ALTER TABLE sensor_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'sensor_id',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('sensor_data', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================
-- 完成提示
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'TimescaleDB 降采样与保留策略配置完成';
    RAISE NOTICE '============================================';
    RAISE NOTICE '保留策略:';
    RAISE NOTICE '  sensor_data (原始): 90天';
    RAISE NOTICE '  sensor_data_10m: 1年';
    RAISE NOTICE '  sensor_data_1h: 5年';
    RAISE NOTICE '  sensor_data_1d: 10年';
    RAISE NOTICE '压缩策略: 7天后自动压缩';
    RAISE NOTICE '============================================';
END $$;
