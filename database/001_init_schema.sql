-- ============================================
-- 应县木塔健康监测系统 - TimescaleDB 初始化脚本
-- ============================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================
-- 1. 楼层信息表
-- ============================================
CREATE TABLE IF NOT EXISTS floors (
    floor_number INTEGER PRIMARY KEY,
    height DECIMAL(10,4) NOT NULL,
    diameter DECIMAL(10,4) NOT NULL,
    beam_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 应县木塔共5层（明层），实际为9层结构（含暗层）
INSERT INTO floors (floor_number, height, diameter, beam_count, column_count, description) VALUES
(1, 9.23, 30.27, 48, 24, '第一层，底层，直径最大'),
(2, 8.50, 25.80, 48, 24, '第二层'),
(3, 7.80, 22.50, 48, 24, '第三层'),
(4, 7.20, 19.80, 48, 24, '第四层'),
(5, 6.50, 17.50, 48, 24, '第五层，顶层');

-- ============================================
-- 2. 传感器信息表
-- ============================================
CREATE TABLE IF NOT EXISTS sensors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(50) UNIQUE NOT NULL,
    floor_number INTEGER REFERENCES floors(floor_number),
    sensor_type VARCHAR(30) NOT NULL,
    x_position DECIMAL(10,4),
    y_position DECIMAL(10,4),
    z_position DECIMAL(10,4),
    status VARCHAR(20) DEFAULT 'active',
    dtu_id VARCHAR(50),
    sampling_interval INTEGER DEFAULT 600,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建传感器索引
CREATE INDEX IF NOT EXISTS idx_sensors_floor ON sensors(floor_number);
CREATE INDEX IF NOT EXISTS idx_sensors_type ON sensors(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensors_status ON sensors(status);

-- ============================================
-- 3. 传感器时序数据表 (超表)
-- ============================================
CREATE TABLE IF NOT EXISTS sensor_data (
    time TIMESTAMPTZ NOT NULL,
    sensor_id UUID NOT NULL REFERENCES sensors(id),
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    raw_data JSONB
);

-- 创建超表
SELECT create_hypertable('sensor_data', 'time', if_not_exists => TRUE);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sensor_data_sensor_time ON sensor_data (sensor_id, time DESC);

-- ============================================
-- 4. 用户表
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'monitor',
    email VARCHAR(100),
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- 创建默认管理员 (密码: admin123)
INSERT INTO users (username, password_hash, role, email, full_name) VALUES
('admin', crypt('admin123', gen_salt('bf')), 'admin', 'admin@pagoda-monitor.com', '系统管理员'),
('monitor', crypt('monitor123', gen_salt('bf')), 'monitor', 'monitor@pagoda-monitor.com', '监测人员'),
('researcher', crypt('research123', gen_salt('bf')), 'researcher', 'research@pagoda-monitor.com', '研究人员')
ON CONFLICT (username) DO NOTHING;

-- ============================================
-- 5. 告警表
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    floor_number INTEGER REFERENCES floors(floor_number),
    sensor_id UUID REFERENCES sensors(id),
    threshold_value DOUBLE PRECISION NOT NULL,
    actual_value DOUBLE PRECISION NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    note TEXT
);

-- 创建告警索引
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_floor ON alerts(floor_number);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);

-- ============================================
-- 6. 告警阈值配置表
-- ============================================
CREATE TABLE IF NOT EXISTS alert_thresholds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parameter_name VARCHAR(50) UNIQUE NOT NULL,
    warning_threshold DOUBLE PRECISION NOT NULL,
    critical_threshold DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20),
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 插入默认阈值
INSERT INTO alert_thresholds (parameter_name, warning_threshold, critical_threshold, unit, description) VALUES
('inter_story_drift_ratio', 0.0025, 0.005, 'rad', '层间位移角: 警告0.25%, 危险0.5%'),
('natural_frequency_drop', 0.05, 0.10, '%', '固有频率下降率: 警告5%, 危险10%'),
('displacement_x', 15.0, 30.0, 'mm', 'X向位移: 警告15mm, 危险30mm'),
('displacement_y', 15.0, 30.0, 'mm', 'Y向位移: 警告15mm, 危险30mm'),
('acceleration', 0.25, 0.50, 'g', '加速度: 警告0.25g, 危险0.50g'),
('temperature', 45.0, 55.0, '°C', '温度: 警告45°C, 危险55°C'),
('moisture_content', 25.0, 35.0, '%', '木材含水率: 警告25%, 危险35%')
ON CONFLICT (parameter_name) DO NOTHING;

-- ============================================
-- 7. 仿真记录表
-- ============================================
CREATE TABLE IF NOT EXISTS simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_type VARCHAR(20) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- ============================================
-- 8. 仿真结果表
-- ============================================
CREATE TABLE IF NOT EXISTS simulation_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID NOT NULL REFERENCES simulations(id),
    floor_number INTEGER,
    max_displacement DOUBLE PRECISION,
    max_stress DOUBLE PRECISION,
    max_acceleration DOUBLE PRECISION,
    natural_frequencies DOUBLE PRECISION[],
    mode_shapes JSONB,
    time_history_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_results_sim ON simulation_results(simulation_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_floor ON simulation_results(floor_number);

-- ============================================
-- 9. 损伤分析表
-- ============================================
CREATE TABLE IF NOT EXISTS damage_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(20) DEFAULT 'processing',
    analysis_window INTEGER NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- 10. 损伤识别结果表
-- ============================================
CREATE TABLE IF NOT EXISTS damage_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES damage_analyses(id),
    floor_number INTEGER NOT NULL,
    element_id INTEGER NOT NULL,
    damage_index DOUBLE PRECISION NOT NULL,
    natural_frequency DOUBLE PRECISION,
    frequency_change DOUBLE PRECISION,
    confidence DOUBLE PRECISION NOT NULL,
    modal_parameters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_damage_results_analysis ON damage_results(analysis_id);
CREATE INDEX IF NOT EXISTS idx_damage_results_floor ON damage_results(floor_number);
CREATE INDEX IF NOT EXISTS idx_damage_results_index ON damage_results(damage_index DESC);

-- ============================================
-- 11. 模态参数表 (用于基准对比)
-- ============================================
CREATE TABLE IF NOT EXISTS modal_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor_number INTEGER NOT NULL,
    mode_order INTEGER NOT NULL,
    natural_frequency DOUBLE PRECISION NOT NULL,
    damping_ratio DOUBLE PRECISION,
    mode_shape JSONB,
    is_baseline BOOLEAN DEFAULT FALSE,
    measured_at TIMESTAMPTZ DEFAULT NOW(),
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_modal_floor_mode ON modal_parameters(floor_number, mode_order);
CREATE INDEX IF NOT EXISTS idx_modal_baseline ON modal_parameters(is_baseline);

-- 插入基准模态参数 (简化模型的前5阶频率)
INSERT INTO modal_parameters (floor_number, mode_order, natural_frequency, damping_ratio, is_baseline, description) VALUES
(1, 1, 0.42, 0.02, TRUE, '第一阶 横向弯曲'),
(1, 2, 0.45, 0.02, TRUE, '第一阶 纵向弯曲'),
(1, 3, 1.18, 0.025, TRUE, '第二阶 横向弯曲'),
(1, 4, 1.25, 0.025, TRUE, '第二阶 纵向弯曲'),
(1, 5, 2.35, 0.03, TRUE, '第三阶 横向+扭转');

-- ============================================
-- 12. DTU设备表
-- ============================================
CREATE TABLE IF NOT EXISTS dtu_devices (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100),
    floor_number INTEGER REFERENCES floors(floor_number),
    ip_address VARCHAR(50),
    status VARCHAR(20) DEFAULT 'online',
    last_heartbeat TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 连续聚合视图 - 10分钟聚合
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_10m
WITH (timescaledb.continuous) AS
SELECT
    sensor_id,
    time_bucket('10 minutes', time) AS bucket,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    STDDEV(value) AS std_value,
    COUNT(*) AS sample_count
FROM sensor_data
GROUP BY sensor_id, time_bucket('10 minutes', time)
WITH NO DATA;

-- 启用实时聚合
ALTER MATERIALIZED VIEW sensor_data_10m SET (timescaledb.materialized_only = false);

-- ============================================
-- 连续聚合视图 - 1小时聚合
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS sensor_data_1h
WITH (timescaledb.continuous) AS
SELECT
    sensor_id,
    time_bucket('1 hour', time) AS bucket,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    STDDEV(value) AS std_value,
    COUNT(*) AS sample_count
FROM sensor_data
GROUP BY sensor_id, time_bucket('1 hour', time)
WITH NO DATA;

ALTER MATERIALIZED VIEW sensor_data_1h SET (timescaledb.materialized_only = false);

-- ============================================
-- 初始化传感器数据
-- ============================================
-- 每层8个传感器: 2位移(X/Y) + 2加速度(X/Y) + 2温湿度 + 2含水率
DO $$
DECLARE
    floor_num INTEGER;
    sensor_idx INTEGER;
    v_device_id VARCHAR(50);
    v_x DECIMAL;
    v_y DECIMAL;
    v_z DECIMAL;
    angle DECIMAL;
    radius DECIMAL;
    floor_height DECIMAL;
BEGIN
    FOR floor_num IN 1..5 LOOP
        SELECT height INTO floor_height FROM floors WHERE floor_number = floor_num;
        
        FOR sensor_idx IN 1..8 LOOP
            -- 计算传感器在圆周上的位置
            angle := (sensor_idx - 1) * 45 * PI() / 180;
            radius := 10.0 - floor_num * 1.5;
            v_x := radius * COS(angle);
            v_y := radius * SIN(angle);
            v_z := floor_height;
            
            IF sensor_idx IN (1, 2) THEN
                -- 位移传感器
                v_device_id := 'DISP-' || floor_num || '-' || CASE WHEN sensor_idx = 1 THEN 'X' ELSE 'Y' END;
                INSERT INTO sensors (device_id, floor_number, sensor_type, x_position, y_position, z_position, dtu_id)
                VALUES (v_device_id, floor_num, CASE WHEN sensor_idx = 1 THEN 'displacement_x' ELSE 'displacement_y' END, v_x, v_y, v_z, 'DTU-' || floor_num);
                
            ELSIF sensor_idx IN (3, 4) THEN
                -- 加速度传感器
                v_device_id := 'ACC-' || floor_num || '-' || CASE WHEN sensor_idx = 3 THEN 'X' ELSE 'Y' END;
                INSERT INTO sensors (device_id, floor_number, sensor_type, x_position, y_position, z_position, dtu_id)
                VALUES (v_device_id, floor_num, CASE WHEN sensor_idx = 3 THEN 'acceleration_x' ELSE 'acceleration_y' END, v_x, v_y, v_z, 'DTU-' || floor_num);
                
            ELSIF sensor_idx IN (5, 6) THEN
                -- 温湿度传感器
                v_device_id := 'TH-' || floor_num || '-' || (sensor_idx - 4);
                INSERT INTO sensors (device_id, floor_number, sensor_type, x_position, y_position, z_position, dtu_id)
                VALUES (v_device_id, floor_num, CASE WHEN sensor_idx = 5 THEN 'temperature' ELSE 'humidity' END, v_x, v_y, v_z, 'DTU-' || floor_num);
                
            ELSE
                -- 木材含水率传感器
                v_device_id := 'MC-' || floor_num || '-' || (sensor_idx - 6);
                INSERT INTO sensors (device_id, floor_number, sensor_type, x_position, y_position, z_position, dtu_id)
                VALUES (v_device_id, floor_num, 'moisture', v_x, v_y, v_z, 'DTU-' || floor_num);
            END IF;
        END LOOP;
        
        -- 插入DTU设备
        INSERT INTO dtu_devices (id, name, floor_number, status)
        VALUES ('DTU-' || floor_num, '第' || floor_num || '层DTU', floor_num, 'online')
        ON CONFLICT (id) DO NOTHING;
    END LOOP;
END $$;

-- ============================================
-- 完成提示
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '应县木塔健康监测系统数据库初始化完成';
    RAISE NOTICE '============================================';
    RAISE NOTICE '创建表: 12个关系表 + 2个连续聚合视图';
    RAISE NOTICE '创建传感器: 5层 × 8个 = 40个传感器';
    RAISE NOTICE '创建DTU设备: 5个';
    RAISE NOTICE '创建用户: admin/monitor/researcher';
    RAISE NOTICE '默认密码: admin123 / monitor123 / research123';
    RAISE NOTICE '============================================';
END $$;
