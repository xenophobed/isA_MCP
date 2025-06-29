-- 海关贸易数据库结构设计
-- Setup script for customs trade database

-- Create database (run this first)
-- CREATE DATABASE customs_trade_db;
-- \c customs_trade_db;

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 企业信息表
CREATE TABLE IF NOT EXISTS companies (
    company_code VARCHAR(18) PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    company_type VARCHAR(20) DEFAULT '进口商', -- 进口商/出口商/货代
    credit_level VARCHAR(10) DEFAULT 'B', -- AA/A/B/C/D
    registration_address TEXT,
    business_scope TEXT,
    established_date DATE,
    annual_trade_volume DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. HS编码表（商品分类）
CREATE TABLE IF NOT EXISTS hs_codes (
    hs_code VARCHAR(10) PRIMARY KEY,
    hs_description_cn VARCHAR(500) NOT NULL,
    hs_description_en VARCHAR(500),
    chapter_code VARCHAR(2),
    chapter_name VARCHAR(100),
    unit_1 VARCHAR(10), -- 第一计量单位
    unit_2 VARCHAR(10), -- 第二计量单位
    import_tax_rate DECIMAL(5,2) DEFAULT 0,
    export_tax_rate DECIMAL(5,2) DEFAULT 0,
    supervision_condition VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 港口信息表
CREATE TABLE IF NOT EXISTS ports (
    port_code VARCHAR(5) PRIMARY KEY,
    port_name VARCHAR(100) NOT NULL,
    port_type VARCHAR(20) DEFAULT '海港', -- 海港/空港/陆港
    country_code VARCHAR(3),
    country_name VARCHAR(50),
    province VARCHAR(50),
    city VARCHAR(50),
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 报关单主表
CREATE TABLE IF NOT EXISTS declarations (
    declaration_no VARCHAR(18) PRIMARY KEY,
    company_code VARCHAR(18) NOT NULL,
    trade_type VARCHAR(2) DEFAULT '进口', -- 进口/出口
    trade_mode VARCHAR(4) DEFAULT '0110', -- 一般贸易/加工贸易等
    transport_mode VARCHAR(2) DEFAULT '2', -- 海运/空运/陆运
    departure_port VARCHAR(5),
    arrival_port VARCHAR(5),
    destination_country VARCHAR(3),
    origin_country VARCHAR(3),
    declare_date DATE NOT NULL,
    customs_date DATE,
    release_date DATE,
    total_amount DECIMAL(15,2) DEFAULT 0,
    currency_code VARCHAR(3) DEFAULT 'USD',
    exchange_rate DECIMAL(8,4) DEFAULT 1.0000,
    rmb_amount DECIMAL(15,2) DEFAULT 0,
    total_tax DECIMAL(15,2) DEFAULT 0,
    customs_officer VARCHAR(50),
    status VARCHAR(20) DEFAULT '已放行',
    risk_level VARCHAR(10) DEFAULT '低风险',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_code) REFERENCES companies(company_code),
    FOREIGN KEY (departure_port) REFERENCES ports(port_code),
    FOREIGN KEY (arrival_port) REFERENCES ports(port_code)
);

-- 5. 商品明细表
CREATE TABLE IF NOT EXISTS goods_details (
    id SERIAL PRIMARY KEY,
    declaration_no VARCHAR(18) NOT NULL,
    seq_no INTEGER NOT NULL,
    hs_code VARCHAR(10) NOT NULL,
    goods_name VARCHAR(200) NOT NULL,
    specifications VARCHAR(500),
    origin_country VARCHAR(3),
    quantity_1 DECIMAL(15,3) DEFAULT 0,
    unit_1 VARCHAR(10),
    quantity_2 DECIMAL(15,3) DEFAULT 0,
    unit_2 VARCHAR(10),
    unit_price DECIMAL(12,4) DEFAULT 0,
    total_price DECIMAL(15,2) DEFAULT 0,
    currency_code VARCHAR(3) DEFAULT 'USD',
    brand VARCHAR(100),
    model VARCHAR(100),
    manufacturer VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (declaration_no) REFERENCES declarations(declaration_no),
    FOREIGN KEY (hs_code) REFERENCES hs_codes(hs_code)
);

-- 6. 集装箱信息表
CREATE TABLE IF NOT EXISTS containers (
    container_no VARCHAR(11) PRIMARY KEY,
    declaration_no VARCHAR(18) NOT NULL,
    container_type VARCHAR(4) DEFAULT 'GP',
    container_size VARCHAR(3) DEFAULT '20',
    seal_no VARCHAR(20),
    gross_weight DECIMAL(10,2) DEFAULT 0,
    loading_port VARCHAR(5),
    discharge_port VARCHAR(5),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (declaration_no) REFERENCES declarations(declaration_no),
    FOREIGN KEY (loading_port) REFERENCES ports(port_code),
    FOREIGN KEY (discharge_port) REFERENCES ports(port_code)
);

-- 7. 运输工具表
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id VARCHAR(20) PRIMARY KEY,
    vehicle_name VARCHAR(100) NOT NULL,
    vehicle_type VARCHAR(20) DEFAULT '船舶', -- 船舶/飞机/车辆
    transport_company VARCHAR(200),
    nationality VARCHAR(3),
    voyage_no VARCHAR(20),
    arrival_date DATE,
    departure_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 贸易伙伴关系表
CREATE TABLE IF NOT EXISTS trade_relationships (
    id SERIAL PRIMARY KEY,
    exporter_code VARCHAR(18),
    importer_code VARCHAR(18),
    trade_frequency INTEGER DEFAULT 0,
    total_trade_amount DECIMAL(15,2) DEFAULT 0,
    main_products TEXT[],
    relationship_start_date DATE,
    relationship_strength DECIMAL(3,2) DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exporter_code) REFERENCES companies(company_code),
    FOREIGN KEY (importer_code) REFERENCES companies(company_code)
);

-- 9. 价格监控表
CREATE TABLE IF NOT EXISTS price_monitoring (
    id SERIAL PRIMARY KEY,
    hs_code VARCHAR(10) NOT NULL,
    reference_price DECIMAL(12,4) NOT NULL,
    price_date DATE NOT NULL,
    price_source VARCHAR(50) DEFAULT '海关估价',
    market_region VARCHAR(50) DEFAULT '全球',
    price_type VARCHAR(20) DEFAULT '进口价', -- 进口价/出口价/市场价
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hs_code) REFERENCES hs_codes(hs_code)
);

-- 10. 风险预警表
CREATE TABLE IF NOT EXISTS risk_alerts (
    alert_id SERIAL PRIMARY KEY,
    declaration_no VARCHAR(18),
    company_code VARCHAR(18),
    risk_type VARCHAR(50) NOT NULL,
    risk_level VARCHAR(10) DEFAULT '中等',
    risk_description TEXT,
    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    handled BOOLEAN DEFAULT FALSE,
    handler VARCHAR(50),
    handle_time TIMESTAMP,
    FOREIGN KEY (declaration_no) REFERENCES declarations(declaration_no),
    FOREIGN KEY (company_code) REFERENCES companies(company_code)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_declarations_company_code ON declarations(company_code);
CREATE INDEX IF NOT EXISTS idx_declarations_declare_date ON declarations(declare_date);
CREATE INDEX IF NOT EXISTS idx_declarations_trade_type ON declarations(trade_type);
CREATE INDEX IF NOT EXISTS idx_declarations_origin_country ON declarations(origin_country);
CREATE INDEX IF NOT EXISTS idx_declarations_rmb_amount ON declarations(rmb_amount);

CREATE INDEX IF NOT EXISTS idx_goods_details_declaration_no ON goods_details(declaration_no);
CREATE INDEX IF NOT EXISTS idx_goods_details_hs_code ON goods_details(hs_code);
CREATE INDEX IF NOT EXISTS idx_goods_details_total_price ON goods_details(total_price);

CREATE INDEX IF NOT EXISTS idx_companies_company_type ON companies(company_type);
CREATE INDEX IF NOT EXISTS idx_companies_credit_level ON companies(credit_level);

CREATE INDEX IF NOT EXISTS idx_hs_codes_chapter_code ON hs_codes(chapter_code);

-- 创建视图以简化查询
CREATE OR REPLACE VIEW v_trade_summary AS
SELECT 
    d.declaration_no,
    c.company_name,
    d.trade_type,
    d.origin_country,
    d.declare_date,
    d.rmb_amount,
    d.status,
    COUNT(g.id) as goods_count
FROM declarations d
JOIN companies c ON d.company_code = c.company_code
LEFT JOIN goods_details g ON d.declaration_no = g.declaration_no
GROUP BY d.declaration_no, c.company_name, d.trade_type, d.origin_country, d.declare_date, d.rmb_amount, d.status;

CREATE OR REPLACE VIEW v_company_trade_stats AS
SELECT 
    c.company_code,
    c.company_name,
    c.company_type,
    COUNT(d.declaration_no) as declaration_count,
    SUM(d.rmb_amount) as total_trade_amount,
    AVG(d.rmb_amount) as avg_trade_amount,
    MAX(d.declare_date) as last_trade_date
FROM companies c
LEFT JOIN declarations d ON c.company_code = d.company_code
GROUP BY c.company_code, c.company_name, c.company_type;

-- 插入一些基础数据
-- 端口数据
INSERT INTO ports (port_code, port_name, port_type, country_code, country_name, province, city) VALUES
('CNSHA', '上海港', '海港', 'CHN', '中国', '上海', '上海'),
('CNSZX', '深圳港', '海港', 'CHN', '中国', '广东', '深圳'),
('CNQIN', '青岛港', '海港', 'CHN', '中国', '山东', '青岛'),
('CNNGB', '宁波港', '海港', 'CHN', '中国', '浙江', '宁波'),
('DEHAM', '汉堡港', '海港', 'DEU', '德国', '汉堡', '汉堡'),
('NLRTM', '鹿特丹港', '海港', 'NLD', '荷兰', '南荷兰', '鹿特丹'),
('USNYC', '纽约港', '海港', 'USA', '美国', '纽约', '纽约'),
('USLAX', '洛杉矶港', '海港', 'USA', '美国', '加利福尼亚', '洛杉矶'),
('JPYOK', '横滨港', '海港', 'JPN', '日本', '神奈川', '横滨'),
('SGSIN', '新加坡港', '海港', 'SGP', '新加坡', '新加坡', '新加坡')
ON CONFLICT (port_code) DO NOTHING;

-- HS编码数据 (汽车零配件相关)
INSERT INTO hs_codes (hs_code, hs_description_cn, hs_description_en, chapter_code, chapter_name, unit_1, unit_2, import_tax_rate) VALUES
('8708100000', '缓冲器及其零件', 'Bumpers and parts thereof', '87', '车辆及其零附件', '千克', '个', 10.0),
('8708210000', '安全带', 'Safety seat belts', '87', '车辆及其零附件', '千克', '套', 8.0),
('8708299000', '其他车身零附件', 'Other parts and accessories of bodies', '87', '车辆及其零附件', '千克', '个', 12.0),
('8708301000', '制动器总成', 'Brake systems', '87', '车辆及其零附件', '千克', '套', 6.0),
('8708309100', '装在盘式制动器上的衬片', 'Brake linings for disc brakes', '87', '车辆及其零附件', '千克', '套', 8.0),
('8708401000', '变速箱及其零件', 'Gear boxes and parts thereof', '87', '车辆及其零附件', '千克', '个', 15.0),
('8708501000', '驱动桥及其零件', 'Drive-axles with differential', '87', '车辆及其零附件', '千克', '个', 10.0),
('8708701000', '车轮及其零附件', 'Road wheels and parts thereof', '87', '车辆及其零附件', '千克', '个', 12.0),
('8708801000', '悬挂系统及其零件', 'Suspension systems and parts thereof', '87', '车辆及其零附件', '千克', '套', 8.0),
('8708910000', '散热器及其零件', 'Radiators and parts thereof', '87', '车辆及其零附件', '千克', '个', 10.0)
ON CONFLICT (hs_code) DO NOTHING;

-- 创建元数据嵌入表 (为语义搜索准备)
CREATE TABLE IF NOT EXISTS metadata_embeddings (
    id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    metadata JSONB,
    semantic_tags TEXT[],
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建向量搜索索引
CREATE INDEX IF NOT EXISTS idx_embeddings_entity_type ON metadata_embeddings(entity_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_entity_name ON metadata_embeddings(entity_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON metadata_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_embeddings_semantic_tags ON metadata_embeddings USING gin(semantic_tags);

-- 用户权限设置
-- 创建数据分析用户
-- CREATE USER data_analyst WITH PASSWORD 'analyst123';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO data_analyst;
-- GRANT USAGE ON SCHEMA public TO data_analyst;