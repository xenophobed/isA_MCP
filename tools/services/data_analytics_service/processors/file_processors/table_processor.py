#!/usr/bin/env python3
"""
Table Processor

Handles table detection and extraction using table transformer models.
Supports both OCR-based and native table extraction methods.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from dataclasses import dataclass
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TableResult:
    """Table extraction result"""
    table_id: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    data: pd.DataFrame
    structure: Dict[str, Any]
    extraction_method: str
    processing_time: float

@dataclass
class CellResult:
    """Table cell extraction result"""
    row_index: int
    col_index: int
    bbox: Tuple[int, int, int, int]
    content: str
    confidence: float

class TableProcessor:
    """
    Table processor using transformer models and traditional methods.
    
    Supports:
    - Table detection in images and documents
    - Table structure recognition
    - Cell content extraction
    - OCR-based table extraction
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.detection_model = self.config.get('detection_model', 'table_transformer')
        self.structure_model = self.config.get('structure_model', 'table_transformer')
        self.ocr_engine = self.config.get('ocr_engine', 'tesseract')
        
        # Table detection thresholds
        self.detection_threshold = self.config.get('detection_threshold', 0.7)
        self.structure_threshold = self.config.get('structure_threshold', 0.5)
    
    async def extract_tables_from_image(self, image_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract tables from image using table transformer.
        
        Args:
            image_path: Path to image file
            options: Processing options
            
        Returns:
            Extracted table results
        """
        try:
            options = options or {}
            
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                return {'error': 'Could not load image', 'success': False}
            
            # Detect tables
            table_detections = await self._detect_tables(img, options)
            
            # Extract each detected table
            extracted_tables = []
            for i, detection in enumerate(table_detections):
                table_result = await self._extract_table_structure(img, detection, f"table_{i}")
                if table_result:
                    extracted_tables.append(table_result)
            
            return {
                'image_path': image_path,
                'tables': [self._table_result_to_dict(table) for table in extracted_tables],
                'table_count': len(extracted_tables),
                'extraction_method': 'table_transformer',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Table extraction from image failed: {e}")
            return {
                'image_path': image_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_tables_from_pdf(self, pdf_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract tables from PDF document.
        
        Args:
            pdf_path: Path to PDF file
            options: Processing options
            
        Returns:
            Extracted table results from all pages
        """
        try:
            options = options or {}
            
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            
            all_tables = []
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling
                img_data = pix.pil_tobytes(format="PNG")
                
                # Convert to OpenCV format
                img_array = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                # Extract tables from page
                page_result = await self.extract_tables_from_image("", {'image_array': img})
                
                if page_result.get('success'):
                    for table_dict in page_result.get('tables', []):
                        table_dict['page_number'] = page_num
                        all_tables.append(table_dict)
            
            doc.close()
            
            return {
                'pdf_path': pdf_path,
                'total_pages': len(doc),
                'tables': all_tables,
                'table_count': len(all_tables),
                'extraction_method': 'pdf_table_transformer',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Table extraction from PDF failed: {e}")
            return {
                'pdf_path': pdf_path,
                'error': str(e),
                'success': False
            }
    
    async def extract_from_ocr(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract tables from OCR results.
        
        Args:
            ocr_results: OCR processing results
            
        Returns:
            Extracted table data
        """
        try:
            tables = []
            
            # Process each page
            for page in ocr_results.get('pages', []):
                page_tables = await self._extract_tables_from_ocr_page(page)
                tables.extend(page_tables)
            
            return {
                'tables': [self._table_result_to_dict(table) for table in tables],
                'table_count': len(tables),
                'extraction_method': 'ocr_pattern_matching',
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Table extraction from OCR failed: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def _detect_tables(self, img: np.ndarray, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect tables in image using table transformer."""
        try:
            # Mock table detection - would use actual table transformer model
            # This is a simplified implementation for demonstration
            
            detections = []
            
            # Simple table detection using contours and lines
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect horizontal and vertical lines
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            
            # Apply morphological operations
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Combine horizontal and vertical lines
            table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0.0)
            
            # Find contours
            contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours that look like tables
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size and aspect ratio
                if w > 200 and h > 100:  # Minimum table size
                    area = cv2.contourArea(contour)
                    rect_area = w * h
                    
                    if area / rect_area > 0.3:  # Reasonable fill ratio
                        detections.append({
                            'bbox': (x, y, w, h),
                            'confidence': 0.8,  # Mock confidence
                            'area': area
                        })
            
            # Sort by confidence (area in this case)
            detections.sort(key=lambda x: x['area'], reverse=True)
            
            return detections
            
        except Exception as e:
            logger.error(f"Table detection failed: {e}")
            return []
    
    async def _extract_table_structure(self, img: np.ndarray, detection: Dict[str, Any], table_id: str) -> Optional[TableResult]:
        """Extract table structure and content."""
        import time
        start_time = time.time()
        
        try:
            # Extract table region
            x, y, w, h = detection['bbox']
            table_img = img[y:y+h, x:x+w]
            
            # Detect table structure (rows and columns)
            structure = await self._detect_table_structure(table_img)
            
            # Extract cell content
            cells = await self._extract_cell_content(table_img, structure)
            
            # Convert to DataFrame
            df = await self._cells_to_dataframe(cells, structure)
            
            return TableResult(
                table_id=table_id,
                bbox=(x, y, w, h),
                confidence=detection['confidence'],
                data=df,
                structure=structure,
                extraction_method='table_transformer',
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Table structure extraction failed: {e}")
            return None
    
    async def _detect_table_structure(self, table_img: np.ndarray) -> Dict[str, Any]:
        """Detect table structure (rows and columns)."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(table_img, cv2.COLOR_BGR2GRAY)
            
            # Detect horizontal lines (row separators)
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
            horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)
            
            # Detect vertical lines (column separators)
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
            vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel)
            
            # Find horizontal line positions
            horizontal_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            row_positions = []
            for contour in horizontal_contours:
                x, y, w, h = cv2.boundingRect(contour)
                if w > table_img.shape[1] * 0.5:  # Line spans at least half the table width
                    row_positions.append(y)
            
            # Find vertical line positions
            vertical_contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            col_positions = []
            for contour in vertical_contours:
                x, y, w, h = cv2.boundingRect(contour)
                if h > table_img.shape[0] * 0.5:  # Line spans at least half the table height
                    col_positions.append(x)
            
            # Sort positions
            row_positions.sort()
            col_positions.sort()
            
            # Add table boundaries
            if 0 not in row_positions:
                row_positions.insert(0, 0)
            if table_img.shape[0] not in row_positions:
                row_positions.append(table_img.shape[0])
            
            if 0 not in col_positions:
                col_positions.insert(0, 0)
            if table_img.shape[1] not in col_positions:
                col_positions.append(table_img.shape[1])
            
            return {
                'rows': len(row_positions) - 1,
                'columns': len(col_positions) - 1,
                'row_positions': row_positions,
                'col_positions': col_positions
            }
            
        except Exception as e:
            logger.error(f"Table structure detection failed: {e}")
            return {'rows': 0, 'columns': 0, 'row_positions': [], 'col_positions': []}
    
    async def _extract_cell_content(self, table_img: np.ndarray, structure: Dict[str, Any]) -> List[CellResult]:
        """Extract content from table cells."""
        try:
            cells = []
            row_positions = structure['row_positions']
            col_positions = structure['col_positions']
            
            # Extract each cell
            for row_idx in range(len(row_positions) - 1):
                for col_idx in range(len(col_positions) - 1):
                    # Cell boundaries
                    y1, y2 = row_positions[row_idx], row_positions[row_idx + 1]
                    x1, x2 = col_positions[col_idx], col_positions[col_idx + 1]
                    
                    # Extract cell image
                    cell_img = table_img[y1:y2, x1:x2]
                    
                    # Perform OCR on cell
                    cell_text = await self._ocr_cell(cell_img)
                    
                    cells.append(CellResult(
                        row_index=row_idx,
                        col_index=col_idx,
                        bbox=(x1, y1, x2-x1, y2-y1),
                        content=cell_text,
                        confidence=0.8  # Mock confidence
                    ))
            
            return cells
            
        except Exception as e:
            logger.error(f"Cell content extraction failed: {e}")
            return []
    
    async def _ocr_cell(self, cell_img: np.ndarray) -> str:
        """Perform OCR on a single cell."""
        try:
            # Preprocess cell image
            gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)
            
            # Enhance text
            gray = cv2.fastNlMeansDenoising(gray)
            
            # Perform OCR
            import pytesseract
            text = pytesseract.image_to_string(gray, config='--psm 8').strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Cell OCR failed: {e}")
            return ""
    
    async def _cells_to_dataframe(self, cells: List[CellResult], structure: Dict[str, Any]) -> pd.DataFrame:
        """Convert cell results to pandas DataFrame."""
        try:
            rows = structure['rows']
            cols = structure['columns']
            
            # Create empty DataFrame
            data = [['' for _ in range(cols)] for _ in range(rows)]
            
            # Fill data from cells
            for cell in cells:
                if cell.row_index < rows and cell.col_index < cols:
                    data[cell.row_index][cell.col_index] = cell.content
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Set column names if first row looks like headers
            if len(data) > 0:
                first_row = data[0]
                if all(cell.strip() for cell in first_row):  # All cells have content
                    df.columns = first_row
                    df = df.iloc[1:]  # Remove header row from data
            
            return df
            
        except Exception as e:
            logger.error(f"DataFrame conversion failed: {e}")
            return pd.DataFrame()
    
    async def _extract_tables_from_ocr_page(self, page_ocr: Dict[str, Any]) -> List[TableResult]:
        """Extract tables from OCR page results."""
        try:
            import time
            start_time = time.time()
            
            tables = []
            text = page_ocr.get('text', '')
            
            # Simple table detection from text patterns
            lines = text.split('\n')
            table_lines = []
            
            for line in lines:
                # Look for lines with multiple whitespace separators
                if len(line.split()) > 2 and '  ' in line:
                    table_lines.append(line)
            
            # Group consecutive table lines
            if len(table_lines) > 2:
                # Convert to DataFrame
                table_data = []
                for line in table_lines:
                    row = [cell.strip() for cell in line.split('  ') if cell.strip()]
                    if row:
                        table_data.append(row)
                
                # Create DataFrame with consistent column count
                if table_data:
                    max_cols = max(len(row) for row in table_data)
                    padded_data = []
                    for row in table_data:
                        padded_row = row + [''] * (max_cols - len(row))
                        padded_data.append(padded_row)
                    
                    df = pd.DataFrame(padded_data)
                    
                    # Create table result
                    table_result = TableResult(
                        table_id=f"ocr_table_{page_ocr.get('page_number', 0)}",
                        bbox=(0, 0, 0, 0),  # Unknown bbox for OCR tables
                        confidence=0.6,
                        data=df,
                        structure={'rows': len(df), 'columns': len(df.columns)},
                        extraction_method='ocr_pattern_matching',
                        processing_time=time.time() - start_time
                    )
                    
                    tables.append(table_result)
            
            return tables
            
        except Exception as e:
            logger.error(f"OCR table extraction failed: {e}")
            return []
    
    def _table_result_to_dict(self, table_result: TableResult) -> Dict[str, Any]:
        """Convert TableResult to dictionary."""
        return {
            'table_id': table_result.table_id,
            'bbox': table_result.bbox,
            'confidence': table_result.confidence,
            'data': table_result.data.to_dict('records'),
            'structure': table_result.structure,
            'extraction_method': table_result.extraction_method,
            'processing_time': table_result.processing_time,
            'row_count': len(table_result.data),
            'column_count': len(table_result.data.columns)
        }
    
    def set_detection_threshold(self, threshold: float):
        """Set table detection threshold."""
        self.detection_threshold = max(0.0, min(1.0, threshold))
    
    def set_structure_threshold(self, threshold: float):
        """Set table structure detection threshold."""
        self.structure_threshold = max(0.0, min(1.0, threshold))
    
    def get_supported_formats(self) -> List[str]:
        """Get supported file formats."""
        return ['image', 'pdf', 'ocr_results']
    
    async def validate_table_structure(self, table_data: pd.DataFrame) -> Dict[str, Any]:
        """Validate extracted table structure."""
        try:
            validation = {
                'is_valid': True,
                'issues': [],
                'quality_score': 1.0,
                'recommendations': []
            }
            
            # Check for empty table
            if table_data.empty:
                validation['is_valid'] = False
                validation['issues'].append('Table is empty')
                return validation
            
            # Check for consistency
            row_lengths = [len(str(cell)) for row in table_data.values for cell in row]
            if len(set(row_lengths)) > len(row_lengths) * 0.5:
                validation['issues'].append('Inconsistent cell content lengths')
                validation['quality_score'] -= 0.2
            
            # Check for empty cells
            empty_cells = table_data.isnull().sum().sum()
            if empty_cells > len(table_data) * len(table_data.columns) * 0.3:
                validation['issues'].append('High number of empty cells')
                validation['quality_score'] -= 0.3
            
            # Generate recommendations
            if validation['quality_score'] < 0.7:
                validation['recommendations'].append('Consider manual review of table structure')
            
            return validation
            
        except Exception as e:
            logger.error(f"Table validation failed: {e}")
            return {'is_valid': False, 'error': str(e)}