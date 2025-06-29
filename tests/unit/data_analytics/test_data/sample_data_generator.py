#!/usr/bin/env python3
"""
Sample data generator for testing data analytics service
Creates realistic test data without mocking
"""

import sqlite3
import pandas as pd
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import os

class SampleDataGenerator:
    """Generates realistic sample data for testing"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_sample_sqlite_db(self) -> str:
        """
        Create a sample SQLite database with realistic structure
        Returns the database file path
        """
        db_path = self.temp_dir / "sample_customs_db.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create customs declaration table
        cursor.execute("""
        CREATE TABLE customs_declaration (
            decl_no VARCHAR(20) PRIMARY KEY,
            company_code VARCHAR(10) NOT NULL,
            trade_date DATE NOT NULL,
            trade_type VARCHAR(10) NOT NULL,
            trade_amount DECIMAL(15,2) NOT NULL,
            currency_code VARCHAR(3) NOT NULL,
            customs_office VARCHAR(10) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create goods detail table
        cursor.execute("""
        CREATE TABLE goods_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decl_no VARCHAR(20) NOT NULL,
            item_no INTEGER NOT NULL,
            hs_code VARCHAR(10) NOT NULL,
            goods_name VARCHAR(200) NOT NULL,
            quantity DECIMAL(12,3) NOT NULL,
            unit_code VARCHAR(3) NOT NULL,
            unit_price DECIMAL(10,4) NOT NULL,
            total_price DECIMAL(15,2) NOT NULL,
            origin_country VARCHAR(3) NOT NULL,
            FOREIGN KEY (decl_no) REFERENCES customs_declaration(decl_no)
        )
        """)
        
        # Create company table
        cursor.execute("""
        CREATE TABLE company (
            company_code VARCHAR(10) PRIMARY KEY,
            company_name VARCHAR(200) NOT NULL,
            company_type VARCHAR(20) NOT NULL,
            registration_no VARCHAR(30) NOT NULL,
            contact_person VARCHAR(50),
            phone VARCHAR(20),
            email VARCHAR(100),
            address TEXT,
            registration_date DATE,
            status VARCHAR(10) NOT NULL
        )
        """)
        
        # Create HS code reference table
        cursor.execute("""
        CREATE TABLE hs_code_ref (
            hs_code VARCHAR(10) PRIMARY KEY,
            description TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            tax_rate DECIMAL(5,2) NOT NULL,
            unit_code VARCHAR(3) NOT NULL,
            supervision_condition VARCHAR(10),
            is_restricted BOOLEAN DEFAULT FALSE
        )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_customs_trade_date ON customs_declaration(trade_date)")
        cursor.execute("CREATE INDEX idx_customs_company ON customs_declaration(company_code)")
        cursor.execute("CREATE INDEX idx_goods_decl_no ON goods_detail(decl_no)")
        cursor.execute("CREATE INDEX idx_goods_hs_code ON goods_detail(hs_code)")
        
        # Insert sample data
        self._insert_sample_companies(cursor)
        self._insert_sample_hs_codes(cursor)
        self._insert_sample_declarations(cursor)
        self._insert_sample_goods(cursor)
        
        conn.commit()
        conn.close()
        
        return str(db_path)
    
    def create_sample_excel_file(self) -> str:
        """
        Create a sample Excel file with multiple sheets
        Returns the Excel file path
        """
        excel_path = self.temp_dir / "sample_trade_data.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Sheet 1: Import declarations
            import_data = self._generate_trade_declarations("IMPORT", 100)
            import_df = pd.DataFrame(import_data)
            import_df.to_excel(writer, sheet_name='Import_Declarations', index=False)
            
            # Sheet 2: Export declarations  
            export_data = self._generate_trade_declarations("EXPORT", 80)
            export_df = pd.DataFrame(export_data)
            export_df.to_excel(writer, sheet_name='Export_Declarations', index=False)
            
            # Sheet 3: Company master data
            company_data = self._generate_company_data(50)
            company_df = pd.DataFrame(company_data)
            company_df.to_excel(writer, sheet_name='Company_Master', index=False)
            
            # Sheet 4: Product catalog
            product_data = self._generate_product_data(200)
            product_df = pd.DataFrame(product_data)
            product_df.to_excel(writer, sheet_name='Product_Catalog', index=False)
        
        return str(excel_path)
    
    def create_sample_csv_file(self) -> str:
        """
        Create a sample CSV file
        Returns the CSV file path
        """
        csv_path = self.temp_dir / "sample_transactions.csv"
        
        # Generate transaction data
        transaction_data = []
        for i in range(500):
            transaction_data.append({
                'transaction_id': f'TXN{str(i+1).zfill(6)}',
                'customer_id': f'CUST{random.randint(1000, 9999)}',
                'product_code': f'PROD{random.randint(100, 999)}',
                'transaction_date': (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
                'quantity': random.randint(1, 100),
                'unit_price': round(random.uniform(10.0, 1000.0), 2),
                'total_amount': 0,  # Will calculate
                'payment_method': random.choice(['CREDIT_CARD', 'CASH', 'BANK_TRANSFER', 'CHECK']),
                'customer_type': random.choice(['INDIVIDUAL', 'BUSINESS', 'GOVERNMENT']),
                'sales_rep': random.choice(['John Smith', 'Jane Doe', 'Mike Johnson', 'Sarah Wilson']),
                'region': random.choice(['NORTH', 'SOUTH', 'EAST', 'WEST']),
                'status': random.choice(['COMPLETED', 'PENDING', 'CANCELLED']),
                'notes': random.choice(['', 'Rush order', 'Bulk discount applied', 'Customer request', ''])
            })
            
            # Calculate total amount
            transaction_data[-1]['total_amount'] = round(
                transaction_data[-1]['quantity'] * transaction_data[-1]['unit_price'], 2
            )
        
        # Save to CSV
        df = pd.DataFrame(transaction_data)
        df.to_csv(csv_path, index=False)
        
        return str(csv_path)
    
    def _insert_sample_companies(self, cursor):
        """Insert sample company data"""
        companies = [
            ('ABC123', 'ABC Trading Co Ltd', 'IMPORT_EXPORT', 'REG001234567', 'John Smith', '021-12345678', 'john@abc.com', '123 Trade St, Shanghai', '2020-01-15', 'ACTIVE'),
            ('XYZ456', 'XYZ International', 'EXPORT', 'REG987654321', 'Jane Doe', '010-87654321', 'jane@xyz.com', '456 Export Ave, Beijing', '2019-05-20', 'ACTIVE'),
            ('DEF789', 'DEF Manufacturing', 'IMPORT', 'REG456789123', 'Mike Wang', '0755-11111111', 'mike@def.com', '789 Industry Rd, Shenzhen', '2018-03-10', 'ACTIVE'),
            ('GHI012', 'GHI Logistics', 'SERVICE', 'REG789123456', 'Lisa Chen', '0571-22222222', 'lisa@ghi.com', '012 Logistics Blvd, Hangzhou', '2021-07-01', 'ACTIVE'),
            ('JKL345', 'JKL Electronics', 'IMPORT_EXPORT', 'REG345678901', 'Tom Liu', '028-33333333', 'tom@jkl.com', '345 Tech Park, Chengdu', '2017-12-05', 'SUSPENDED')
        ]
        
        cursor.executemany(
            "INSERT INTO company VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            companies
        )
    
    def _insert_sample_hs_codes(self, cursor):
        """Insert sample HS code data"""
        hs_codes = [
            ('8471301000', 'Portable automatic data processing machines weighing not more than 10kg', 'Electronics', 13.0, 'SET', 'A', False),
            ('8528721100', 'Colour reception apparatus for television', 'Electronics', 13.0, 'SET', 'A', False),
            ('6204620000', 'Women\'s or girls\' trousers of cotton', 'Textiles', 16.0, 'PCS', 'A', False),
            ('4011101900', 'New pneumatic tyres of rubber for passenger cars', 'Automotive', 20.0, 'PCS', 'A', False),
            ('2710199100', 'Motor gasoline', 'Chemicals', 1.0, 'LTR', 'B', True),
            ('1001990000', 'Wheat and meslin, other', 'Agriculture', 65.0, 'KGM', 'C', False),
            ('7208510000', 'Flat-rolled products of iron or non-alloy steel', 'Metals', 0.0, 'KGM', 'A', False),
            ('3004905990', 'Other medicaments', 'Pharmaceuticals', 4.0, 'KGM', 'D', True),
            ('8703231000', 'Motor cars with cylinder capacity of 1000-1500cc', 'Automotive', 25.0, 'SET', 'A', False),
            ('0303140000', 'Frozen skipjack or stripe-bellied bonito', 'Food', 10.0, 'KGM', 'A', False)
        ]
        
        cursor.executemany(
            "INSERT INTO hs_code_ref VALUES (?, ?, ?, ?, ?, ?, ?)",
            hs_codes
        )
    
    def _insert_sample_declarations(self, cursor):
        """Insert sample customs declarations"""
        declarations = []
        companies = ['ABC123', 'XYZ456', 'DEF789', 'GHI012']
        trade_types = ['IMPORT', 'EXPORT']
        currencies = ['USD', 'EUR', 'JPY', 'CNY']
        customs_offices = ['SHA01', 'PEK01', 'SZX01', 'HGH01', 'CDU01']
        statuses = ['DECLARED', 'EXAMINED', 'RELEASED', 'COMPLETED']
        
        for i in range(50):
            decl_no = f'SHA{datetime.now().year}{str(i+1).zfill(6)}'
            company = random.choice(companies)
            trade_date = (datetime.now() - timedelta(days=random.randint(1, 365))).strftime('%Y-%m-%d')
            trade_type = random.choice(trade_types)
            amount = round(random.uniform(1000.0, 1000000.0), 2)
            currency = random.choice(currencies)
            office = random.choice(customs_offices)
            status = random.choice(statuses)
            
            declarations.append((decl_no, company, trade_date, trade_type, amount, currency, office, status))
        
        cursor.executemany(
            "INSERT INTO customs_declaration (decl_no, company_code, trade_date, trade_type, trade_amount, currency_code, customs_office, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            declarations
        )
    
    def _insert_sample_goods(self, cursor):
        """Insert sample goods details"""
        # Get declaration numbers
        cursor.execute("SELECT decl_no FROM customs_declaration")
        decl_nos = [row[0] for row in cursor.fetchall()]
        
        hs_codes = ['8471301000', '8528721100', '6204620000', '4011101900', '2710199100', 
                   '1001990000', '7208510000', '3004905990', '8703231000', '0303140000']
        
        goods_names = [
            'Laptop Computer', 'Television Set', 'Cotton Trousers', 'Car Tyre', 'Motor Gasoline',
            'Wheat', 'Steel Sheets', 'Medicine', 'Motor Car', 'Frozen Fish'
        ]
        
        units = ['SET', 'SET', 'PCS', 'PCS', 'LTR', 'KGM', 'KGM', 'KGM', 'SET', 'KGM']
        countries = ['US', 'DE', 'CN', 'JP', 'KR', 'IT', 'FR', 'UK', 'CA', 'AU']
        
        goods = []
        for decl_no in decl_nos:
            # Random number of items per declaration
            item_count = random.randint(1, 5)
            for item_no in range(1, item_count + 1):
                idx = random.randint(0, len(hs_codes) - 1)
                quantity = round(random.uniform(1.0, 1000.0), 3)
                unit_price = round(random.uniform(1.0, 1000.0), 4)
                total_price = round(quantity * unit_price, 2)
                
                goods.append((
                    decl_no, item_no, hs_codes[idx], goods_names[idx],
                    quantity, units[idx], unit_price, total_price, random.choice(countries)
                ))
        
        cursor.executemany(
            "INSERT INTO goods_detail (decl_no, item_no, hs_code, goods_name, quantity, unit_code, unit_price, total_price, origin_country) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            goods
        )
    
    def _generate_trade_declarations(self, trade_type: str, count: int) -> List[Dict]:
        """Generate trade declaration data for Excel"""
        declarations = []
        for i in range(count):
            declarations.append({
                'Declaration_No': f'{trade_type[:3]}{datetime.now().year}{str(i+1).zfill(6)}',
                'Company_Code': f'COMP{random.randint(100, 999)}',
                'Company_Name': f'Company {random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}',
                'Trade_Date': (datetime.now() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
                'Trade_Type': trade_type,
                'Total_Amount': round(random.uniform(1000.0, 500000.0), 2),
                'Currency': random.choice(['USD', 'EUR', 'JPY', 'CNY']),
                'Customs_Office': random.choice(['SHA01', 'PEK01', 'SZX01', 'HGH01']),
                'Status': random.choice(['DECLARED', 'EXAMINED', 'RELEASED', 'COMPLETED']),
                'Agent_Code': f'AGT{random.randint(100, 999)}',
                'Port_Code': random.choice(['CNSHA', 'CNPEK', 'CNSZX', 'CNHGH']),
                'Transport_Mode': random.choice(['SEA', 'AIR', 'LAND', 'RAIL']),
                'Package_Count': random.randint(1, 100),
                'Gross_Weight': round(random.uniform(100.0, 10000.0), 2),
                'Net_Weight': round(random.uniform(50.0, 9000.0), 2)
            })
        return declarations
    
    def _generate_company_data(self, count: int) -> List[Dict]:
        """Generate company master data for Excel"""
        company_types = ['MANUFACTURER', 'TRADER', 'AGENT', 'LOGISTICS', 'RETAILER']
        regions = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'CENTRAL']
        
        companies = []
        for i in range(count):
            companies.append({
                'Company_Code': f'COMP{str(i+100).zfill(3)}',
                'Company_Name': f'Company {random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)} Ltd',
                'Company_Type': random.choice(company_types),
                'Registration_No': f'REG{random.randint(100000000, 999999999)}',
                'Legal_Representative': f'{random.choice(["John", "Jane", "Mike", "Sarah", "David"])} {random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])}',
                'Contact_Phone': f'0{random.randint(10, 99)}-{random.randint(10000000, 99999999)}',
                'Email': f'contact{i}@company{i}.com',
                'Region': random.choice(regions),
                'Registration_Date': (datetime.now() - timedelta(days=random.randint(365, 3650))).strftime('%Y-%m-%d'),
                'Credit_Rating': random.choice(['AAA', 'AA', 'A', 'BBB', 'BB', 'B']),
                'Annual_Turnover': round(random.uniform(100000.0, 50000000.0), 2),
                'Employee_Count': random.randint(10, 1000),
                'Status': random.choice(['ACTIVE', 'INACTIVE', 'SUSPENDED'])
            })
        return companies
    
    def _generate_product_data(self, count: int) -> List[Dict]:
        """Generate product catalog data for Excel"""
        categories = ['ELECTRONICS', 'TEXTILES', 'MACHINERY', 'CHEMICALS', 'FOOD', 'AUTOMOTIVE', 'METALS']
        
        products = []
        for i in range(count):
            category = random.choice(categories)
            products.append({
                'Product_Code': f'PROD{str(i+1000).zfill(4)}',
                'Product_Name': f'{category.lower().title()} Product {i+1}',
                'Category': category,
                'HS_Code': f'{random.randint(1000, 9999)}{random.randint(100000, 999999)}',
                'Brand': f'Brand{random.choice(string.ascii_uppercase)}',
                'Model': f'Model{random.randint(100, 999)}',
                'Specification': f'Spec {random.randint(1, 10)} x {random.randint(1, 10)} x {random.randint(1, 10)}',
                'Unit_of_Measure': random.choice(['PCS', 'SET', 'KGM', 'LTR', 'MTR']),
                'Unit_Price': round(random.uniform(1.0, 1000.0), 2),
                'Supplier_Code': f'SUP{random.randint(100, 999)}',
                'Country_of_Origin': random.choice(['CN', 'US', 'DE', 'JP', 'KR', 'IT']),
                'Quality_Grade': random.choice(['A', 'B', 'C']),
                'Is_Regulated': random.choice([True, False]),
                'Shelf_Life_Days': random.randint(30, 3650) if category == 'FOOD' else None,
                'Storage_Requirement': random.choice(['NORMAL', 'REFRIGERATED', 'FROZEN', 'DRY']) if category == 'FOOD' else 'NORMAL'
            })
        return products
    
    def create_test_database_config(self, db_type: str = "sqlite") -> Dict[str, Any]:
        """Create test database configuration"""
        if db_type == "sqlite":
            db_path = self.create_sample_sqlite_db()
            return {
                "type": "sqlite", 
                "database": db_path,
                "include_data_analysis": True,
                "sample_size": 100
            }
        else:
            # For PostgreSQL/MySQL testing in CI/CD environments
            return {
                "type": db_type,
                "host": "localhost",
                "port": 5432 if db_type == "postgresql" else 3306,
                "database": "test_db",
                "username": "test_user",
                "password": "test_pass",
                "include_data_analysis": True,
                "sample_size": 100
            }
    
    def create_test_file_configs(self) -> Dict[str, Dict[str, Any]]:
        """Create test file configurations"""
        excel_path = self.create_sample_excel_file()
        csv_path = self.create_sample_csv_file()
        
        return {
            "excel": {
                "file_path": excel_path,
                "file_type": "excel",
                "include_data_analysis": True
            },
            "csv": {
                "file_path": csv_path,
                "file_type": "csv", 
                "include_data_analysis": True
            }
        }
    
    def get_expected_metadata_structure(self) -> Dict[str, Any]:
        """Get expected metadata structure for validation"""
        return {
            "required_keys": ["source_info", "tables", "columns", "relationships", "indexes"],
            "source_info_keys": ["type", "total_tables", "total_columns", "total_relationships"],
            "table_keys": ["table_name", "schema_name", "table_type", "record_count"],
            "column_keys": ["table_name", "column_name", "data_type", "is_nullable", "ordinal_position"]
        }