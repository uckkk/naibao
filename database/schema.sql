-- 纯奶粉喂养APP 数据库表结构
-- PostgreSQL 15+

-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    nickname VARCHAR(50),
    avatar_url VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 奶粉品牌表（被 feedings / user_formula_selections 引用，需先创建）
CREATE TABLE formula_brands (
    id SERIAL PRIMARY KEY,
    name_cn VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    logo_url VARCHAR(255),
    market_share DECIMAL(5,2),
    features TEXT[],
    official_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 宝宝表
CREATE TABLE babies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    nickname VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(255),
    birth_date DATE NOT NULL,
    birth_time TIME NOT NULL,
    gender VARCHAR(10), -- 'male' or 'female'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 喂养记录表
CREATE TABLE feedings (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL, -- 奶量（ml）
    feeding_time TIMESTAMP NOT NULL,
    formula_brand_id INTEGER REFERENCES formula_brands(id),
    formula_series_name VARCHAR(100),
    scoops INTEGER, -- 勺数
    device_id VARCHAR(100), -- 记录设备ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_feedings_baby_id ON feedings(baby_id);
CREATE INDEX idx_feedings_feeding_time ON feedings(feeding_time);
CREATE INDEX idx_feedings_user_id ON feedings(user_id);

-- 生长数据表
CREATE TABLE growth_records (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    record_date DATE NOT NULL,
    weight DECIMAL(5,2), -- 体重（kg）
    height INTEGER, -- 身高（cm）
    daily_milk_amount INTEGER, -- 日总奶量（ml）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(baby_id, record_date)
);

CREATE INDEX idx_growth_records_baby_id ON growth_records(baby_id);
CREATE INDEX idx_growth_records_date ON growth_records(record_date);

-- 用户偏好表
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    default_amount INTEGER, -- 默认奶量
    adjustment_pattern INTEGER DEFAULT 0, -- 调整模式（如：总是+20ml）
    input_method VARCHAR(20), -- 'direct', 'quick', 'manual'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, baby_id)
);

-- 奶粉官方要求表
CREATE TABLE formula_specifications (
    id SERIAL PRIMARY KEY,
    brand_id INTEGER NOT NULL REFERENCES formula_brands(id),
    series_name VARCHAR(100),
    age_range VARCHAR(20), -- '0-6', '6-12'
    
    -- 勺数规格
    scoop_weight_gram DECIMAL(5,2) NOT NULL, -- 一勺重量（g）
    scoop_ml DECIMAL(5,2) NOT NULL, -- 一勺对应水量（ml）
    
    -- 冲泡要求
    water_temp_min INTEGER, -- 建议水温最低（℃）
    water_temp_max INTEGER, -- 建议水温最高（℃）
    mixing_method TEXT, -- 冲泡方法说明
    
    -- 喂养建议
    feeding_frequency TEXT,
    daily_amount_min INTEGER,
    daily_amount_max INTEGER,
    
    -- 数据来源
    data_source VARCHAR(255), -- 数据来源
    verified_at TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(brand_id, series_name, age_range)
);

-- 用户选择的奶粉
CREATE TABLE user_formula_selections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    brand_id INTEGER NOT NULL REFERENCES formula_brands(id),
    series_name VARCHAR(100),
    age_range VARCHAR(20),
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, baby_id)
);

-- 卫健委标准配置表
CREATE TABLE health_standards (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL, -- 版本号：2025, 2026
    type VARCHAR(50) NOT NULL, -- 'weight', 'height', 'milk_by_age', 'milk_by_weight', 'weight_gain', 'height_gain'
    month_min INTEGER,
    month_max INTEGER,
    data JSONB NOT NULL, -- 标准数据（JSON格式）
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_standards_version ON health_standards(version);
CREATE INDEX idx_health_standards_type ON health_standards(type);

-- 邀请码表
CREATE TABLE invite_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(6) UNIQUE NOT NULL,
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    creator_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_by INTEGER REFERENCES users(id),
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invite_codes_code ON invite_codes(code);
CREATE INDEX idx_invite_codes_baby_id ON invite_codes(baby_id);

-- 家庭成员表
CREATE TABLE family_members (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'member', -- 'admin', 'member', 'guest'
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(baby_id, user_id)
);

CREATE INDEX idx_family_members_baby_id ON family_members(baby_id);

-- 设备表（用于多设备同步）
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    device_id VARCHAR(100) NOT NULL,
    device_type VARCHAR(20), -- 'ios', 'android', 'wechat', 'harmony'
    device_name VARCHAR(100),
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, device_id)
);

-- 操作日志表（用于数据审计）
CREATE TABLE operation_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action VARCHAR(50) NOT NULL, -- 'create', 'update', 'delete'
    entity_type VARCHAR(50) NOT NULL, -- 'feeding', 'growth', 'baby'
    entity_id INTEGER NOT NULL,
    before_data JSONB,
    after_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 喂奶间隔和提醒设置表
CREATE TABLE feeding_settings (
    id SERIAL PRIMARY KEY,
    baby_id INTEGER NOT NULL REFERENCES babies(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    day_interval INTEGER DEFAULT 3,        -- 白天间隔（小时）
    night_interval INTEGER DEFAULT 5,      -- 晚上间隔（小时）
    reminder_enabled BOOLEAN DEFAULT true, -- 提醒开关
    advance_minutes INTEGER DEFAULT 15,    -- 提前提醒分钟数
    day_start_hour INTEGER DEFAULT 6,       -- 白天开始时间（默认6点）
    day_end_hour INTEGER DEFAULT 18,        -- 白天结束时间（默认18点）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(baby_id)
);

CREATE INDEX idx_feeding_settings_baby_id ON feeding_settings(baby_id);

CREATE INDEX idx_operation_logs_user_id ON operation_logs(user_id);
CREATE INDEX idx_operation_logs_entity ON operation_logs(entity_type, entity_id);

-- 会员表
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_type VARCHAR(20) NOT NULL, -- 'lifetime', 'monthly'
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'expired', 'cancelled'
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP, -- lifetime为NULL
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
