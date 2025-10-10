"""
Database Schema Manager

Handles creating and managing database schema for test plan data.
"""

import logging
from .base_importer import BaseImporter

logger = logging.getLogger(__name__)


class SchemaManager(BaseImporter):
    """Manages database schema creation and updates"""
    
    def create_schema(self):
        """Create complete database schema for test plan data"""
        logger.info("Creating database schema...")
        
        # Drop existing tables in correct order (dependencies first)
        self._drop_existing_tables()
        
        # Create new tables
        self._create_projects_table()
        self._create_pics_reference_table()
        self._create_project_pics_table()
        self._create_specifications_table()
        self._create_test_cases_table()
        self._create_conditions_table()
        self._create_test_mappings_table()
        
        # Commit schema changes
        self.commit()
        
        logger.info("Schema created successfully")
    
    def _drop_existing_tables(self):
        """Drop existing tables in correct order"""
        tables_to_drop = [
            "project_pics",      # Has foreign keys to projects and pics_reference
            "test_cases",        # Has foreign key to specifications
            "conditions",        # Has foreign key to specifications
            "test_mappings",     # Standalone
            "band_mappings",     # Old table (if exists)
            "pics_reference",    # Referenced by project_pics
            "projects",          # Referenced by project_pics
            "specifications"     # Referenced by test_cases and conditions
        ]
        
        for table in tables_to_drop:
            try:
                self.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            except Exception as e:
                logger.debug(f"Could not drop table {table}: {e}")
    
    def _create_projects_table(self):
        """Create projects table for customer/project data"""
        self.execute("""
            CREATE TABLE projects (
                project_id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                customer_name VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_pics_reference_table(self):
        """Create PICS reference table for global definitions"""
        self.execute("""
            CREATE TABLE pics_reference (
                pics_id VARCHAR PRIMARY KEY,
                specification VARCHAR NOT NULL,
                description TEXT,
                item_type VARCHAR,  -- 'band', 'feature', 'capability', etc.
                band_info JSON,     -- If it's a band: {band_name, band_type, frequency_range}
                allowed_values VARCHAR,
                default_value VARCHAR,
                status VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_project_pics_table(self):
        """Create project PICS table for customer-specific data"""
        # Create sequence for project_pics id
        try:
            self.execute("CREATE SEQUENCE project_pics_id_seq")
        except:
            pass  # Sequence might already exist
        
        self.execute("""
            CREATE TABLE project_pics (
                id INTEGER PRIMARY KEY DEFAULT nextval('project_pics_id_seq'),
                project_id VARCHAR NOT NULL,
                pics_id VARCHAR NOT NULL,
                supported BOOLEAN DEFAULT FALSE,
                current_value VARCHAR,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id),
                FOREIGN KEY (pics_id) REFERENCES pics_reference(pics_id),
                UNIQUE(project_id, pics_id)
            )
        """)
    
    def _create_specifications_table(self):
        """Create specifications table"""
        self.execute("""
            CREATE TABLE specifications (
                spec_id VARCHAR PRIMARY KEY,
                spec_name VARCHAR,
                spec_version VARCHAR,
                spec_type VARCHAR,  -- 'PICS' or 'TEST'
                sheet_name VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def _create_test_cases_table(self):
        """Create test cases table"""
        self.execute("""
            CREATE TABLE test_cases (
                test_id VARCHAR,
                spec_id VARCHAR,
                clause VARCHAR,
                title VARCHAR,
                release VARCHAR,
                applicability_condition VARCHAR,
                applicability_comment TEXT,
                specific_ics VARCHAR,
                specific_ixit VARCHAR,
                num_executions VARCHAR,
                release_other_rat VARCHAR,
                standard VARCHAR,
                version VARCHAR,
                PRIMARY KEY (test_id, spec_id),
                FOREIGN KEY (spec_id) REFERENCES specifications(spec_id)
            )
        """)
    
    def _create_conditions_table(self):
        """Create conditions table"""
        self.execute("""
            CREATE TABLE conditions (
                condition_id VARCHAR,
                spec_id VARCHAR,
                condition_type VARCHAR,  -- 'C-condition', 'PICS', 'Other'
                definition TEXT,
                table_index INTEGER,
                raw_data JSON,
                PRIMARY KEY (condition_id, spec_id),
                FOREIGN KEY (spec_id) REFERENCES specifications(spec_id)
            )
        """)
    
    def _create_test_mappings_table(self):
        """Create test mappings table"""
        self.execute("""
            CREATE TABLE test_mappings (
                source_test_id VARCHAR,
                target_test_id VARCHAR,
                source_spec VARCHAR,
                target_spec VARCHAR,
                mapping_type VARCHAR,  -- 'direct', 'pattern', 'manual', 'extracted'
                confidence FLOAT,
                PRIMARY KEY (source_test_id, target_test_id, source_spec, target_spec)
            )
        """)
    
    def verify_schema(self):
        """Verify that all required tables exist"""
        required_tables = [
            'projects', 'pics_reference', 'project_pics',
            'specifications', 'test_cases', 'conditions', 'test_mappings'
        ]
        
        result = self.fetch_all("SHOW TABLES")
        existing_tables = {row[0] for row in result}
        
        missing_tables = set(required_tables) - existing_tables
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("All required tables exist")
        return True