-- Schema updates for proper data organization

-- 1. Projects table for customer/project specific data
CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR PRIMARY KEY,
    project_name VARCHAR,
    customer_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. PICS Reference table (global PICS definitions from template)
DROP TABLE IF EXISTS pics_reference CASCADE;
CREATE TABLE pics_reference (
    pics_id VARCHAR PRIMARY KEY,        -- e.g., 'A.4.3-3/1'
    specification VARCHAR NOT NULL,     -- e.g., '3GPP TS 36.521-2'
    description TEXT,                   -- Description of the PICS item
    item_type VARCHAR,                  -- 'band', 'feature', 'capability', etc.
    band_info JSON,                     -- If it's a band: {band_name, band_type, frequency_range}
    allowed_values VARCHAR,             -- Allowed values/settings
    default_value VARCHAR,              -- Default value
    status VARCHAR,                     -- Status information
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pics_spec (specification),
    INDEX idx_pics_type (item_type)
);

-- 3. Project PICS table (customer-specific PICS support)
DROP TABLE IF EXISTS project_pics CASCADE;
CREATE TABLE project_pics (
    id INTEGER PRIMARY KEY,
    project_id VARCHAR NOT NULL,
    pics_id VARCHAR NOT NULL,           -- References pics_reference.pics_id
    supported BOOLEAN DEFAULT FALSE,    -- Whether customer's UE supports this
    current_value VARCHAR,              -- Customer's specific value
    comments TEXT,                      -- Any customer-specific comments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (pics_id) REFERENCES pics_reference(pics_id),
    UNIQUE(project_id, pics_id),
    INDEX idx_project_pics (project_id, supported)
);

-- 3. Parameter configuration tables from 3GPP specs (global reference data)
CREATE TABLE IF NOT EXISTS parameter_tables (
    table_id VARCHAR PRIMARY KEY,  -- e.g., "7.3.2.4.1-1"
    table_title VARCHAR,
    section VARCHAR,               -- e.g., "7.3.2.4.1"
    specification VARCHAR,         -- e.g., "TS 38.521-1"
    parameters JSON,               -- Parameter definitions and values
    raw_data JSON,                 -- Original table data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Test parameter configurations (links test cases to parameter tables)
CREATE TABLE IF NOT EXISTS test_parameter_configs (
    test_id VARCHAR,
    table_id VARCHAR,
    parameter_set JSON,  -- Specific parameter combinations for this test
    PRIMARY KEY (test_id, table_id),
    FOREIGN KEY (table_id) REFERENCES parameter_tables(table_id)
);

-- 5. Project test combinations (generated for specific project)
CREATE TABLE IF NOT EXISTS project_test_combinations (
    combination_id VARCHAR PRIMARY KEY,
    project_id VARCHAR NOT NULL,
    test_id VARCHAR NOT NULL,
    parameter_values JSON,  -- Actual parameter values for this combination
    applicable BOOLEAN,     -- Based on PICS capabilities
    execution_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    INDEX idx_project_test (project_id, test_id)
);