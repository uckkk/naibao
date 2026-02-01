-- 初始化基础数据

-- 插入卫健委2025标准数据
INSERT INTO health_standards (version, type, month_min, month_max, data, is_active) VALUES
-- 按体重奶量标准
('2025', 'milk_by_weight', NULL, NULL, '{"min": 120, "max": 150, "recommended": 135, "unit": "ml/kg/day"}', true),

-- 按月龄奶量标准
('2025', 'milk_by_age', 0, 1, '{"min": 600, "max": 700, "unit": "ml/day"}', true),
('2025', 'milk_by_age', 1, 3, '{"min": 700, "max": 900, "unit": "ml/day"}', true),
('2025', 'milk_by_age', 3, 6, '{"min": 800, "max": 1000, "unit": "ml/day"}', true),
('2025', 'milk_by_age', 6, 12, '{"min": 900, "max": 1100, "unit": "ml/day"}', true),

-- 日均增重标准
('2025', 'weight_gain', 0, 3, '{"min": 0.025, "max": 0.035, "recommended": 0.030, "unit": "kg/day"}', true),
('2025', 'weight_gain', 3, 6, '{"min": 0.015, "max": 0.025, "recommended": 0.020, "unit": "kg/day"}', true),
('2025', 'weight_gain', 6, 12, '{"min": 0.010, "max": 0.015, "recommended": 0.012, "unit": "kg/day"}', true),

-- 日均增高标准
('2025', 'height_gain', 0, 3, '{"min": 8, "max": 11, "recommended": 9.5, "unit": "mm/day"}', true),
('2025', 'height_gain', 3, 6, '{"min": 6, "max": 9, "recommended": 7.5, "unit": "mm/day"}', true),
('2025', 'height_gain', 6, 12, '{"min": 4, "max": 6, "recommended": 5, "unit": "mm/day"}', true);

-- 插入常见奶粉品牌（根据设计图，真实品牌数据）
INSERT INTO formula_brands (name_cn, name_en, market_share, features, official_url) VALUES
('飞鹤', 'FIRMUS', 17.5, ARRAY['A2奶源', '专利OPO', 'HMO配方'], 'https://www.feihe.com'),
('金领冠', 'JINLINGGUAN', 12.3, ARRAY['α+β蛋白', '专利核苷酸', 'A2奶源'], 'https://www.jinlingguan.com'),
('君乐宝', 'JUNLEBAO', 8.9, ARRAY['自有牧场', '80+专利', '全产业链'], 'https://www.junlebao.com'),
('贝因美', 'BEINGMATE', 4.2, ARRAY['双蛋白防护', '5种HMO', 'α-乳白蛋白'], 'https://www.beingmate.com'),
('澳优', 'AUSNUTRIA', 3.8, ARRAY['全球羊奶第一', '荷兰奶源', '海普诺凯'], 'https://www.ausnutria.com'),
('爱他美', 'APTAMIL', 9.5, ARRAY['德国原装', 'HMO配方', '高端品质'], 'https://www.aptamil.com.cn'),
('合生元', 'BIOSTIME', 7.2, ARRAY['SN-2技术', '乳桥蛋白', 'HMO配方'], 'https://www.biostime.com'),
('伊利', 'YILI', 6.8, ARRAY['全球乳业5强', '奥运品质', '全产业链'], 'https://www.yili.com'),
('蒙牛', 'MENGNIU', 5.5, ARRAY['欧洲技术', '乳都核心区', '营养健康'], 'https://www.mengniu.com.cn'),
('美素佳儿', 'FRISO', 8.7, ARRAY['荷兰原装', '自家牧场', '皇家系列'], 'https://www.friso.com.cn'),
('惠氏', 'WYETH', 7.9, ARRAY['启赋系列', 'ILLUMA', '高端配方'], 'https://www.wyethnutrition.com.cn'),
('a2', 'A2', 6.3, ARRAY['A2蛋白质', '新西兰原装', '至初系列'], 'https://www.a2nutrition.com.cn');

-- 插入奶粉规格（示例数据，实际需要通过数据获取方案补充）
INSERT INTO formula_specifications (brand_id, series_name, age_range, scoop_weight_gram, scoop_ml, water_temp_min, water_temp_max, mixing_method, is_verified) VALUES
((SELECT id FROM formula_brands WHERE name_cn = 'a2'), '至初系列', '0-6', 4.5, 30, 40, 50, '1. 将适量温水（40-50℃）倒入奶瓶\n2. 使用配套量勺，每勺4.5g\n3. 加入奶粉后摇匀\n4. 测试温度后喂养', false),
((SELECT id FROM formula_brands WHERE name_cn = '金领冠'), 'α+β蛋白系列', '0-6', 4.3, 30, 40, 50, '1. 洗净双手和奶瓶\n2. 将30ml温水（40-50℃）倒入奶瓶\n3. 加入一平勺（4.3g）奶粉\n4. 摇匀后测试温度', false);

