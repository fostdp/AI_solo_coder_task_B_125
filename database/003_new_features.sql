-- ============================================================
-- 003_new_features.sql - 新功能扩展表
-- 朝代对比、榫卯工艺数字化、倒塌模拟、虚拟登塔
-- ============================================================

-- ======== 1. 朝代对比模块 ========

CREATE TABLE IF NOT EXISTS dynasty_pagodas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    dynasty VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL DEFAULT 'China',
    build_year VARCHAR(50),
    height DOUBLE PRECISION NOT NULL,
    floor_count INTEGER NOT NULL,
    structural_type VARCHAR(50) NOT NULL,
    column_count INTEGER,
    beam_count INTEGER,
    bracket_set_type VARCHAR(50),
    foundation_type VARCHAR(50),
    roof_weight DOUBLE PRECISION,
    description TEXT,
    seismic_philosophy TEXT,
    structural_params JSONB NOT NULL DEFAULT '{}',
    timber_properties JSONB DEFAULT '{}',
    joint_properties JSONB DEFAULT '{}',
    image_url VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO dynasty_pagodas (name, dynasty, country, build_year, height, floor_count, structural_type, column_count, beam_count, bracket_set_type, foundation_type, roof_weight, description, seismic_philosophy, structural_params, timber_properties, joint_properties) VALUES
('应县木塔', '辽代', 'China', '1056年', 67.31, 5, '楼阁式-内槽外槽双筒', 24, 8, '七踩三翘', '石质台基', 5800,
 '世界现存最古老最高的木结构塔式建筑，采用内外双槽结构体系，暗层形成刚性环箍',
 '以柔克刚：通过榫卯半刚性连接吸收地震能量，层间柔性变形耗能',
 '{"floor_heights": [6.59, 5.49, 4.99, 4.59, 4.09], "floor_diameters": [30.27, 22.65, 18.46, 15.28, 12.10], "inner_diameters": [15.2, 12.0, 10.0, 8.5, 7.0], "wall_thickness": [2.0, 1.8, 1.6, 1.4, 1.2], "base_diameter": 30.27}',
 '{"E_L": 10000, "E_R": 800, "E_T": 500, "G_LR": 750, "G_LT": 650, "G_RT": 40, "density": 500}',
 '{"type": "mortise_tenon", "rotational_stiffness": 1e8, "yield_moment": 1e5, "gap": 0.001}'
),
('法隆寺五重塔', '飞鸟时代', 'Japan', '607年', 32.45, 5, '心柱式-自承重', 16, 4, '出三跳', '掘立柱-础石', 2100,
 '日本现存最古老的木结构塔，采用心柱贯穿结构，各层独立框架围绕心柱',
 '柔性屈服：层间允许大变形，心柱如同定海神针提供恢复力，层间错位耗能',
 '{"floor_heights": [8.50, 6.60, 5.40, 4.20, 3.75], "floor_diameters": [10.80, 9.20, 7.80, 6.50, 5.20], "inner_diameters": [3.5, 3.0, 2.5, 2.0, 1.5], "wall_thickness": [0.8, 0.7, 0.6, 0.5, 0.4], "base_diameter": 10.80, "shinbashira_diameter": 0.6, "shinbashira_height": 32.45}',
 '{"E_L": 9000, "E_R": 600, "E_T": 400, "G_LR": 600, "G_LT": 500, "G_RT": 30, "density": 450}',
 '{"type": "nuki_joint", "rotational_stiffness": 5e7, "yield_moment": 5e4, "gap": 0.002}'
),
('佛光寺东大殿', '唐代', 'China', '857年', 12.0, 1, '殿阁式-单层厅堂', 36, 12, '四铺作', '石质台基', 3500,
 '中国现存最大的唐代木结构建筑，梁架结构雄大，斗拱比例宏大',
 '刚柔并济：宏大斗拱体系分散荷载，梁柱刚性连接与柔性榫卯结合',
 '{"floor_heights": [12.0], "floor_diameters": [34.0], "inner_diameters": [24.0], "wall_thickness": [1.5], "base_diameter": 34.0, "ridge_height": 12.0}',
 '{"E_L": 10500, "E_R": 750, "E_T": 480, "G_LR": 700, "G_LT": 600, "G_RT": 35, "density": 520}',
 '{"type": "mortise_tenon", "rotational_stiffness": 1.2e8, "yield_moment": 1.2e5, "gap": 0.0008}'
),
('东大寺南大门', '镰仓时代', 'Japan', '1199年', 25.46, 2, '天竺样-大佛样', 18, 6, '六铺作', '掘立柱-础石', 4200,
 '日本镰仓时代大佛样代表建筑，贯通式梁柱结构，构件尺度巨大',
 '贯抜構法：横向贯木贯穿柱身形成整体框架，大变形下的结构稳定性',
 '{"floor_heights": [15.0, 10.46], "floor_diameters": [28.0, 22.0], "inner_diameters": [18.0, 14.0], "wall_thickness": [1.2, 1.0], "base_diameter": 28.0}',
 '{"E_L": 9500, "E_R": 650, "E_T": 420, "G_LR": 650, "G_LT": 550, "G_RT": 32, "density": 480}',
 '{"type": "nuki_through", "rotational_stiffness": 8e7, "yield_moment": 8e4, "gap": 0.0015}'
);

CREATE TABLE IF NOT EXISTS dynasty_comparisons (
    id SERIAL PRIMARY KEY,
    pagoda_a_id INTEGER REFERENCES dynasty_pagodas(id) NOT NULL,
    pagoda_b_id INTEGER REFERENCES dynasty_pagodas(id) NOT NULL,
    comparison_type VARCHAR(50) NOT NULL,
    seismic_philosophy_diff TEXT,
    structural_diff JSONB DEFAULT '{}',
    frequency_comparison JSONB DEFAULT '{}',
    displacement_comparison JSONB DEFAULT '{}',
    energy_dissipation JSONB DEFAULT '{}',
    conclusion TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======== 2. 榫卯工艺数字化模块 ========

CREATE TABLE IF NOT EXISTS mortise_tenon_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    chinese_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    dynasty_origin VARCHAR(50),
    description TEXT NOT NULL,
    mechanical_model JSONB NOT NULL DEFAULT '{}',
    geometric_params JSONB DEFAULT '{}',
    application TEXT,
    image_url VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO mortise_tenon_types (name, chinese_name, category, dynasty_origin, description, mechanical_model, geometric_params, application) VALUES
('straight_tenon', '直榫', 'beam_column', '先秦',
 '最常见的榫卯类型，榫头直插入卯眼中，依靠摩擦力和木材膨胀固定',
 '{"model_type": "bilinear", "elastic_stiffness": 1e8, "yield_moment": 80000, "ultimate_moment": 120000, "yield_rotation": 0.005, "ultimate_rotation": 0.03, "damping_ratio": 0.05, "pinching_factor": 0.3, "damage_accumulation": true}',
 '{"tenon_length": 0.15, "tenon_width": 0.08, "tenon_height": 0.12, "mortise_depth": 0.16, "mortise_width": 0.085, "mortise_height": 0.125, "clearance": 0.003}',
 '梁柱连接、枋木连接'
),
('dovetail_tenon', '燕尾榫', 'beam_column', '先秦',
 '榫头呈梯形，根部宽端部窄，插入后自动锁紧，抗拔出能力强',
 '{"model_type": "trilinear", "elastic_stiffness": 1.5e8, "yield_moment": 100000, "ultimate_moment": 160000, "yield_rotation": 0.004, "ultimate_rotation": 0.025, "post_yield_ratio": 0.3, "damping_ratio": 0.06, "pinching_factor": 0.25, "damage_accumulation": true}',
 '{"tenon_length": 0.12, "tenon_root_width": 0.10, "tenon_tip_width": 0.06, "tenon_height": 0.10, "mortise_depth": 0.13, "mortise_root_width": 0.065, "mortise_tip_width": 0.105, "taper_ratio": 0.6}',
 '枋木对接、阑额与柱连接'
),
('cross_tenon', '十字榫', 'cross_joint', '汉唐',
 '两根构件十字交叉连接，上下各切去一半互相咬合，抗扭能力强',
 '{"model_type": "bilinear", "elastic_stiffness": 8e7, "yield_moment": 60000, "ultimate_moment": 90000, "yield_rotation": 0.006, "ultimate_rotation": 0.035, "damping_ratio": 0.07, "pinching_factor": 0.35, "torsional_stiffness": 5e7}',
 '{"half_cut_depth": 0.06, "cross_width": 0.10, "cross_height": 0.12, "notch_length": 0.08, "tolerance": 0.002}',
 '十字交叉枋、井干结构'
),
('through_tenon', '透榫', 'through_beam', '唐宋',
 '榫头贯穿柱身，露出端部用木楔固定，可拆卸维修，日本大佛样常用',
 '{"model_type": "trilinear", "elastic_stiffness": 1.2e8, "yield_moment": 95000, "ultimate_moment": 150000, "yield_rotation": 0.0045, "ultimate_rotation": 0.028, "post_yield_ratio": 0.35, "damping_ratio": 0.055, "pinching_factor": 0.2, "damage_accumulation": true}',
 '{"tenon_length": 0.35, "tenon_width": 0.07, "tenon_height": 0.10, "column_diameter": 0.45, "wedge_width": 0.03, "wedge_height": 0.05, "through_clearance": 0.005}',
 '贯木穿柱、大佛样结构'
),
('angle_brace_tenon', '斜撑榫', 'bracing', '宋辽',
 '斜向构件与柱或梁的连接，斜撑提供抗侧刚度，常见于木塔暗层',
 '{"model_type": "bilinear_with_gap", "elastic_stiffness": 6e7, "yield_moment": 45000, "ultimate_moment": 70000, "yield_rotation": 0.007, "ultimate_rotation": 0.04, "gap": 0.002, "damping_ratio": 0.08, "pinching_factor": 0.4}',
 '{"brace_angle": 45, "tenon_length": 0.10, "tenon_width": 0.06, "tenon_height": 0.08, "brace_section": "0.08x0.08"}',
 '暗层斜撑、叉手'
),
('bucket_arch_joint', '斗拱节点', 'bracket_set', '唐辽',
 '斗拱各组件间的层叠式连接，栌斗-泥道栱-华栱-散斗逐层叠合，传递荷载并耗能',
 '{"model_type": "multi_linear", "elastic_stiffness": 2e8, "yield_moment": 130000, "ultimate_moment": 200000, "yield_rotation": 0.003, "ultimate_rotation": 0.02, "stages": [{"range": [0, 0.003], "stiffness": 2e8}, {"range": [0.003, 0.008], "stiffness": 6e7}, {"range": [0.008, 0.015], "stiffness": 2e7}, {"range": [0.015, 0.02], "stiffness": 5e6}], "damping_ratio": 0.04, "pinching_factor": 0.15, "vertical_load_effect": true}',
 '{"lu_dou_size": "0.4x0.4x0.15", "ni_dao_gong_length": 0.8, "hua_gong_length": 0.6, "san_dou_size": "0.2x0.2x0.08", "layer_count": 3, "overhang_length": 0.5}',
 '檐下斗拱、平座斗拱'
);

CREATE TABLE IF NOT EXISTS mortise_tenon_simulations (
    id SERIAL PRIMARY KEY,
    joint_type_id INTEGER REFERENCES mortise_tenon_types(id) NOT NULL,
    simulation_type VARCHAR(50) NOT NULL DEFAULT 'cyclic',
    load_protocol JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    result JSONB DEFAULT '{}',
    hysteresis_data JSONB DEFAULT '{}',
    energy_dissipation JSONB DEFAULT '{}',
    stiffness_degradation JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ======== 3. 倒塌模拟模块 ========

CREATE TABLE IF NOT EXISTS collapse_simulations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    earthquake_magnitude DOUBLE PRECISION NOT NULL,
    earthquake_pga DOUBLE PRECISION NOT NULL,
    earthquake_wave JSONB DEFAULT '{}',
    duration DOUBLE PRECISION NOT NULL DEFAULT 30.0,
    time_step DOUBLE PRECISION NOT NULL DEFAULT 0.01,
    status VARCHAR(20) DEFAULT 'pending',
    collapse_mode VARCHAR(50),
    collapse_time DOUBLE PRECISION,
    collapse_floor INTEGER,
    max_drift_ratio DOUBLE PRECISION,
    max_base_shear DOUBLE PRECISION,
    ductility_factor DOUBLE PRECISION,
    overstrength_factor DOUBLE PRECISION,
    ultimate_capacity JSONB DEFAULT '{}',
    time_history JSONB DEFAULT '{}',
    failure_sequence JSONB DEFAULT '{}',
    input_energy JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ======== 4. 虚拟登塔体验模块 ========

CREATE TABLE IF NOT EXISTS virtual_tower_paths (
    id SERIAL PRIMARY KEY,
    path_name VARCHAR(100) NOT NULL,
    description TEXT,
    waypoints JSONB NOT NULL DEFAULT '[]',
    total_duration DOUBLE PRECISION DEFAULT 600.0,
    difficulty VARCHAR(20) DEFAULT 'easy',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO virtual_tower_paths (path_name, description, waypoints, total_duration, difficulty) VALUES
('朝圣之路', '从台基一层逐层攀登至塔刹，体验完整的木塔内部空间序列',
 '[{"x": 15, "y": 0, "z": 0, "name": "入口", "duration": 30}, {"x": 10, "y": 2, "z": 0, "name": "台基", "duration": 60}, {"x": 8, "y": 6.59, "z": 5, "name": "一层内槽", "duration": 90}, {"x": 6, "y": 12.08, "z": 3, "name": "二层平座", "duration": 90}, {"x": 5, "y": 17.57, "z": -2, "name": "三层暗层", "duration": 80}, {"x": 4, "y": 22.56, "z": 1, "name": "四层佛殿", "duration": 80}, {"x": 3, "y": 27.15, "z": 0, "name": "五层明层", "duration": 90}, {"x": 0, "y": 32, "z": 0, "name": "塔刹", "duration": 60}]',
 600.0, 'medium'
);

CREATE TABLE IF NOT EXISTS virtual_experience_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    path_id INTEGER REFERENCES virtual_tower_paths(id),
    current_floor INTEGER DEFAULT 1,
    current_position JSONB DEFAULT '{"x": 15, "y": 0, "z": 0}',
    wind_speed DOUBLE PRECISION DEFAULT 0.0,
    wind_vibration_amplitude DOUBLE PRECISION DEFAULT 0.0,
    earthquake_intensity DOUBLE PRECISION DEFAULT 0.0,
    experience_duration DOUBLE PRECISION DEFAULT 0.0,
    sensory_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
