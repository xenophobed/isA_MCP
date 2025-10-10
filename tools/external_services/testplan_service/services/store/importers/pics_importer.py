"""
PICS Data Importer

Handles importing PICS reference data and customer-specific PICS support data.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any

from .base_importer import BaseImporter
import sys
from pathlib import Path
# Add the base path to sys.path for imports
base_module_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(base_module_path))

# from services.processor.corrected_interlab_reader import CorrectedInterlabReader  # TODO: Fix this import

logger = logging.getLogger(__name__)


class PICSImporter(BaseImporter):
    """Importer for PICS data"""
    
    def import_reference_from_template(self, template_path: str = None):
        """
        Import PICS reference data from Interlab template Excel
        
        Args:
            template_path: Path to template Excel file
        """
        if template_path is None:
            template_path = self.base_path / "data_source/test_cases/Interlab_EVO_Feature_Spreadsheet_Template_All_20250920.xlsx"
        
        logger.info(f"\n📖 Importing PICS reference from template: {Path(template_path).name}")
        
        if not Path(template_path).exists():
            logger.error(f"Template file not found: {template_path}")
            return
        
        # Use CorrectedInterlabReader to extract all PICS items
        # TODO: Implement PICS template reading
        # reader = CorrectedInterlabReader(str(template_path))
        logger.warning("PICS template reading not yet implemented - skipping")
        return  # Early return until we implement the reader
        # profile = reader.read_supported_pics_profile()
        
        import_count = 0
        band_count = 0
        
        for pics_id, item in profile.pics_items.items():
            # Determine item type and extract band info if applicable
            item_type = self._determine_pics_item_type(pics_id)
            band_info = None
            
            if item_type == 'band':
                band_info = self._extract_band_info_from_pics(pics_id, item.description)
                band_count += 1
            
            # Insert into pics_reference table
            self.execute("""
                INSERT OR REPLACE INTO pics_reference
                (pics_id, specification, description, item_type, band_info, 
                 allowed_values, default_value, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pics_id,
                item.specification,
                item.description,
                item_type,
                json.dumps(band_info) if band_info else None,
                item.allowed_values,
                item.current_value,
                item.status
            ))
            import_count += 1
        
        self.commit()
        logger.info(f"  ✅ Imported {import_count} PICS reference items")
        logger.info(f"     Including {band_count} band-related items")
        
        self._log_import_statistics()
    
    def import_customer_pics(self, project_id: str, customer_excel_path: str):
        """
        Import customer-specific PICS support from their Excel file
        
        Args:
            project_id: Project identifier
            customer_excel_path: Path to customer's Excel file
        """
        logger.info(f"\n👥 Importing customer PICS for project {project_id}")
        
        if not Path(customer_excel_path).exists():
            logger.error(f"Customer Excel file not found: {customer_excel_path}")
            return
        
        # Use CorrectedInterlabReader to extract customer's supported PICS  
        # TODO: Implement customer PICS reading
        # reader = CorrectedInterlabReader(str(customer_excel_path))
        logger.warning("Customer PICS reading not yet implemented - skipping")
        return  # Early return until we implement the reader
        profile = reader.read_supported_pics_profile()
        
        import_count = 0
        supported_count = 0
        
        for pics_id, item in profile.pics_items.items():
            # Only import if this PICS ID exists in reference
            ref_check = self.fetch_one(
                "SELECT 1 FROM pics_reference WHERE pics_id = ?",
                (pics_id,)
            )
            
            if not ref_check:
                logger.debug(f"Skipping {pics_id} - not in reference data")
                continue
            
            # Insert customer's PICS support
            # Use INSERT OR IGNORE + UPDATE to handle unique constraint properly
            self.execute("""
                INSERT OR IGNORE INTO project_pics
                (project_id, pics_id, supported, current_value, comments)
                VALUES (?, ?, ?, ?, ?)
            """, (
                project_id,
                pics_id,
                item.supported,
                item.current_value,
                f"Status: {item.status}" if item.status else None
            ))
            
            # Update if already exists
            self.execute("""
                UPDATE project_pics 
                SET supported = ?, current_value = ?, comments = ?, updated_at = CURRENT_TIMESTAMP
                WHERE project_id = ? AND pics_id = ?
            """, (
                item.supported,
                item.current_value,
                f"Status: {item.status}" if item.status else None,
                project_id,
                pics_id
            ))
            
            import_count += 1
            if item.supported:
                supported_count += 1
        
        self.commit()
        logger.info(f"  ✅ Imported {import_count} customer PICS items")
        logger.info(f"     {supported_count} marked as supported")
        
        self._log_customer_support_summary(project_id)
    
    def _determine_pics_item_type(self, pics_id: str) -> str:
        """Determine the type of PICS item"""
        # Band-related patterns
        if 'A.4.3-3/' in pics_id:  # Single carrier bands
            return 'band'
        elif 'A.4.3-4' in pics_id:  # CA configurations
            return 'band'
        elif 'A.4.6' in pics_id:    # CA bands
            return 'band'
        elif 'A.4.3-6' in pics_id:  # DC configurations
            return 'band'
        # Feature patterns
        elif 'A.4.1' in pics_id or 'A.4.2' in pics_id:
            return 'feature'
        # Capability patterns
        elif 'PC_' in pics_id:
            return 'capability'
        else:
            return 'other'
    
    def _extract_band_info_from_pics(self, pics_id: str, description: str) -> Dict[str, Any]:
        """Extract band information from PICS ID and description"""
        band_info = {
            'band_name': None,
            'band_type': None,
            'frequency_range': None
        }
        
        # Single carrier bands (A.4.3-3/X)
        if match := re.match(r'A\.4\.3-3/(\d+)', pics_id):
            band_num = int(match.group(1))
            # TDD bands are 33-53 according to 3GPP TS 36.101
            if 33 <= band_num <= 53:
                band_info['band_name'] = f'eTDD{band_num}'
                band_info['band_type'] = 'TDD'
            else:
                band_info['band_name'] = f'eFDD{band_num}'
                band_info['band_type'] = 'FDD'
        
        # CA bands (A.4.6.1-3/CA_XYZ)
        elif match := re.match(r'A\.4\.6\.1-3/(.+)', pics_id):
            band_info['band_name'] = match.group(1)
            band_info['band_type'] = 'CA'
        
        # DC configurations
        elif 'A.4.3-6' in pics_id:
            band_info['band_type'] = 'DC'
            if match := re.search(r'DC_(.+)', pics_id):
                band_info['band_name'] = f'DC_{match.group(1)}'
        
        # Try to extract frequency from description
        if freq_match := re.search(r'(\d+)\s*MHz', description):
            band_info['frequency_range'] = freq_match.group(0)
        
        return band_info
    
    def _log_import_statistics(self):
        """Log PICS reference import statistics"""
        result = self.fetch_all("""
            SELECT specification, COUNT(*) as cnt, 
                   SUM(CASE WHEN item_type = 'band' THEN 1 ELSE 0 END) as band_cnt
            FROM pics_reference 
            GROUP BY specification
        """)
        
        logger.info("\n  PICS Reference by specification:")
        for spec, total, bands in result:
            logger.info(f"    {spec}: {total} items ({bands} bands)")
    
    def _log_customer_support_summary(self, project_id: str):
        """Log customer PICS support summary"""
        result = self.fetch_all("""
            SELECT pr.item_type, COUNT(*) as total, 
                   SUM(CASE WHEN pp.supported THEN 1 ELSE 0 END) as supported
            FROM project_pics pp
            JOIN pics_reference pr ON pp.pics_id = pr.pics_id
            WHERE pp.project_id = ?
            GROUP BY pr.item_type
        """, (project_id,))
        
        logger.info("\n  Customer support by type:")
        for item_type, total, supported in result:
            logger.info(f"    {item_type}: {supported}/{total} supported")