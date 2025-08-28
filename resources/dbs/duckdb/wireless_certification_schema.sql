-- Wireless Router Certification Testing Database Schema - Pure Business Data
-- Designed for 300K+ records with optimized 30-parameter queries
-- Compatible with existing DataStorageService, DuckDBSinkAdapter, and SQLQueryService
-- User/company access control handled by MCP resources (not database-level)

-- Products table for router models
CREATE TABLE IF NOT EXISTS certification_products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    model_number VARCHAR(100) NOT NULL UNIQUE,
    product_type VARCHAR(50) DEFAULT 'wireless_router',
    frequency_bands VARCHAR(200), -- e.g., "2.4GHz,5GHz,6GHz"
    wifi_standards VARCHAR(100), -- e.g., "802.11ax,802.11ac,802.11n"
    max_power_output DECIMAL(10,3), -- dBm
    antenna_type VARCHAR(100),
    antenna_gain DECIMAL(5,2), -- dBi
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Certification projects
CREATE TABLE IF NOT EXISTS certification_projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) UNIQUE NOT NULL,
    product_id INTEGER NOT NULL REFERENCES certification_products(id) ON DELETE CASCADE,
    project_name VARCHAR(255) NOT NULL,
    project_type VARCHAR(50) DEFAULT 'initial', -- 'initial', 'modification', 'renewal'
    certification_standards VARCHAR(200), -- 'FCC,IC,CE' combinations
    project_status VARCHAR(50) DEFAULT 'quote_requested',
    start_date DATE,
    target_completion_date DATE,
    actual_completion_date DATE,
    total_cost DECIMAL(12,2),
    assigned_engineer VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main testing records table - optimized for 300K+ records with 30-parameter queries
CREATE TABLE IF NOT EXISTS certification_test_records (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES certification_projects(id) ON DELETE CASCADE,
    test_session_id VARCHAR(50) NOT NULL,
    certification_standard VARCHAR(10) NOT NULL, -- FCC, IC, CE
    test_category VARCHAR(50) NOT NULL, -- EMC, RF, SAR, Safety
    test_type VARCHAR(100) NOT NULL, -- specific test name
    test_date DATE NOT NULL,
    test_time TIME,
    
    -- Core measurement parameters (30 key parameters for quick queries)
    -- RF Power Parameters
    conducted_power_dbm DECIMAL(8,3),
    radiated_power_dbm DECIMAL(8,3),
    eirp_dbm DECIMAL(8,3), -- Effective Isotropic Radiated Power
    peak_power_dbm DECIMAL(8,3),
    average_power_dbm DECIMAL(8,3),
    
    -- Frequency Parameters
    center_frequency_mhz DECIMAL(10,3),
    frequency_tolerance_ppm DECIMAL(8,3),
    occupied_bandwidth_khz DECIMAL(10,2),
    channel_bandwidth_mhz DECIMAL(8,2),
    spurious_emissions_dbm DECIMAL(8,3),
    
    -- EMC Parameters
    conducted_emissions_dbuv DECIMAL(8,2),
    radiated_emissions_dbuv_m DECIMAL(8,2),
    harmonic_emissions_dbm DECIMAL(8,3),
    esd_immunity_kv DECIMAL(6,2), -- Electrostatic Discharge
    rf_immunity_v_m DECIMAL(8,3), -- RF Immunity V/m
    
    -- Environmental Parameters
    temperature_celsius DECIMAL(5,2),
    humidity_percent DECIMAL(5,2),
    atmospheric_pressure_kpa DECIMAL(7,2),
    
    -- SAR Parameters (Specific Absorption Rate)
    sar_1g_w_kg DECIMAL(8,4), -- SAR 1 gram tissue
    sar_10g_w_kg DECIMAL(8,4), -- SAR 10 gram tissue
    
    -- Performance Parameters
    throughput_mbps DECIMAL(10,2),
    range_meters DECIMAL(8,2),
    latency_ms DECIMAL(8,3),
    packet_error_rate_percent DECIMAL(6,4),
    
    -- Antenna Parameters
    antenna_gain_dbi DECIMAL(6,2),
    antenna_efficiency_percent DECIMAL(5,2),
    
    -- Power Supply Parameters
    input_voltage_v DECIMAL(6,2),
    input_current_a DECIMAL(8,4),
    power_consumption_w DECIMAL(8,2),
    
    -- Test Result Parameters
    test_result VARCHAR(20) DEFAULT 'pending', -- pass, fail, conditional, pending
    margin_db DECIMAL(6,2), -- safety margin from limit
    limit_value DECIMAL(10,3), -- regulatory limit
    
    -- Metadata
    test_engineer VARCHAR(100),
    equipment_used VARCHAR(500),
    test_notes TEXT,
    retest_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test limits and standards reference
CREATE TABLE IF NOT EXISTS certification_regulatory_limits (
    id SERIAL PRIMARY KEY,
    certification_standard VARCHAR(10) NOT NULL, -- FCC, IC, CE
    test_category VARCHAR(50) NOT NULL,
    test_type VARCHAR(100) NOT NULL,
    frequency_range_start_mhz DECIMAL(10,3),
    frequency_range_end_mhz DECIMAL(10,3),
    limit_value DECIMAL(10,3) NOT NULL,
    limit_unit VARCHAR(20) NOT NULL,
    measurement_distance_m DECIMAL(6,2),
    notes TEXT,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Certification certificates
CREATE TABLE IF NOT EXISTS certification_certificates (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES certification_projects(id) ON DELETE CASCADE,
    certification_standard VARCHAR(10) NOT NULL,
    certificate_number VARCHAR(100) UNIQUE NOT NULL,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    status VARCHAR(20) DEFAULT 'valid', -- valid, expired, revoked, pending
    certificate_url VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cost tracking
CREATE TABLE IF NOT EXISTS certification_project_costs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES certification_projects(id) ON DELETE CASCADE,
    cost_category VARCHAR(50) NOT NULL, -- testing, certification, travel, equipment
    cost_subcategory VARCHAR(100),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    cost_date DATE NOT NULL,
    invoice_number VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes for 300K+ records and 30-parameter queries
CREATE INDEX idx_cert_test_records_project_standard 
    ON certification_test_records(project_id, certification_standard);
    
CREATE INDEX idx_cert_test_records_date_category 
    ON certification_test_records(test_date, test_category);
    
CREATE INDEX idx_cert_test_records_result_type 
    ON certification_test_records(test_result, test_type);
    
CREATE INDEX idx_cert_test_records_frequency 
    ON certification_test_records(center_frequency_mhz);
    
CREATE INDEX idx_cert_test_records_power 
    ON certification_test_records(eirp_dbm, conducted_power_dbm);

-- Composite indexes for common multi-parameter queries
CREATE INDEX idx_cert_test_records_multi_rf 
    ON certification_test_records(certification_standard, center_frequency_mhz, eirp_dbm, test_result);

CREATE INDEX idx_cert_test_records_multi_emc 
    ON certification_test_records(test_category, conducted_emissions_dbuv, radiated_emissions_dbuv_m, test_result);

-- Views for common queries (compatible with existing DataAnalyticsService)
CREATE VIEW v_certification_project_summary AS
SELECT 
    p.id as project_id,
    p.project_code,
    pr.product_name,
    pr.model_number,
    p.certification_standards,
    p.project_status,
    COUNT(tr.id) as total_tests,
    COUNT(CASE WHEN tr.test_result = 'pass' THEN 1 END) as passed_tests,
    COUNT(CASE WHEN tr.test_result = 'fail' THEN 1 END) as failed_tests,
    AVG(tr.eirp_dbm) as avg_eirp,
    MAX(tr.sar_1g_w_kg) as max_sar,
    p.total_cost,
    p.start_date,
    p.target_completion_date
FROM certification_projects p
JOIN certification_products pr ON p.product_id = pr.id
LEFT JOIN certification_test_records tr ON p.id = tr.project_id
GROUP BY p.id, p.project_code, pr.product_name, 
         pr.model_number, p.certification_standards, p.project_status,
         p.total_cost, p.start_date, p.target_completion_date;

-- View for regulatory compliance checking
CREATE VIEW v_certification_compliance_status AS
SELECT 
    tr.id as record_id,
    tr.project_id,
    tr.certification_standard,
    tr.test_type,
    tr.test_result,
    tr.eirp_dbm,
    tr.conducted_emissions_dbuv,
    tr.sar_1g_w_kg,
    rl.limit_value,
    rl.limit_unit,
    (tr.eirp_dbm - rl.limit_value) as power_margin_db,
    CASE 
        WHEN tr.test_result = 'pass' AND tr.eirp_dbm <= rl.limit_value THEN 'compliant'
        WHEN tr.test_result = 'fail' OR tr.eirp_dbm > rl.limit_value THEN 'non_compliant'
        ELSE 'pending_review'
    END as compliance_status
FROM certification_test_records tr
LEFT JOIN certification_regulatory_limits rl ON (
    tr.certification_standard = rl.certification_standard 
    AND tr.test_type = rl.test_type
    AND tr.center_frequency_mhz BETWEEN rl.frequency_range_start_mhz AND rl.frequency_range_end_mhz
);

-- Insert sample regulatory limits
INSERT INTO certification_regulatory_limits 
(certification_standard, test_category, test_type, frequency_range_start_mhz, frequency_range_end_mhz, limit_value, limit_unit, measurement_distance_m, notes) 
VALUES
('FCC', 'RF', 'Conducted Power', 2400, 2483.5, 20, 'dBm', 0, 'FCC Part 15.247 2.4GHz ISM band'),
('FCC', 'RF', 'Radiated Power', 2400, 2483.5, 20, 'dBm EIRP', 3, 'FCC Part 15.247 2.4GHz ISM band'),
('FCC', 'EMC', 'Conducted Emissions', 0.15, 30, 60, 'dBuV', 0, 'FCC Part 15 Class B'),
('FCC', 'EMC', 'Radiated Emissions', 30, 1000, 40, 'dBuV/m', 3, 'FCC Part 15 Class B'),
('CE', 'RF', 'EIRP', 2400, 2483.5, 20, 'dBm', 0, 'ETSI EN 300 328'),
('CE', 'RF', 'Power Spectral Density', 2400, 2483.5, 10, 'dBm/MHz', 0, 'ETSI EN 300 328'),
('CE', 'SAR', 'SAR 1g', 0, 6000, 2.0, 'W/kg', 0, 'EN 62311 1g tissue'),
('CE', 'SAR', 'SAR 10g', 0, 6000, 2.0, 'W/kg', 0, 'EN 62311 10g tissue'),
('IC', 'RF', 'EIRP', 2400, 2483.5, 20, 'dBm', 0, 'RSS-247 Issue 4'),
('IC', 'SAR', 'SAR 1g', 0, 6000, 1.6, 'W/kg', 0, 'RSS-102 Issue 6')
ON CONFLICT DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE certification_products IS 'Wireless router models for certification testing';
COMMENT ON TABLE certification_projects IS 'Certification projects with status tracking and cost management';
COMMENT ON TABLE certification_test_records IS 'Main testing data with 30 measurement parameters optimized for 300K+ records';
COMMENT ON TABLE certification_regulatory_limits IS 'Reference table for regulatory compliance limits';
COMMENT ON TABLE certification_certificates IS 'Issued certificates with tracking and expiry management';
COMMENT ON TABLE certification_project_costs IS 'Detailed cost tracking per project and category';