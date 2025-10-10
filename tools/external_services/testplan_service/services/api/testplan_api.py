#!/usr/bin/env python3
"""
TestPlan Generation API using DuckDB + Polars Engine

High-performance API for generating 3GPP test plans from XLSX input to XLSX output.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime
import uuid

from ..engine.testplan_engine import TestPlanEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="3GPP TestPlan Generation Service",
    description="High-performance test plan generation using DuckDB + Polars",
    version="1.0.0"
)


class TestPlanGenerator:
    """TestPlan generation service using the DuckDB + Polars engine"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        logger.info(f"Temporary directory: {self.temp_dir}")
    
    def detect_specification_from_xlsx(self, xlsx_path: Path) -> Optional[str]:
        """
        Detect 3GPP specification from XLSX file structure
        
        Args:
            xlsx_path: Path to XLSX file
            
        Returns:
            Detected spec_id or None
        """
        try:
            # Read Excel file and check sheet names
            xl_file = pd.ExcelFile(xlsx_path)
            sheet_names = xl_file.sheet_names
            
            # Look for 3GPP specification patterns in sheet names
            for sheet_name in sheet_names:
                if "36.521" in sheet_name or "36521" in sheet_name:
                    return "36521"
                elif "34.123" in sheet_name or "34123" in sheet_name:
                    return "34123"
                elif "38.521" in sheet_name or "38521" in sheet_name:
                    return "38521"
                elif "37.521" in sheet_name or "37521" in sheet_name:
                    return "37521"
            
            # Also check file name
            file_name = xlsx_path.name
            if "36.521" in file_name or "36521" in file_name:
                return "36521"
            elif "34.123" in file_name or "34123" in file_name:
                return "34123"
            elif "38.521" in file_name or "38521" in file_name:
                return "38521"
            elif "37.521" in file_name or "37521" in file_name:
                return "37521"
                
            logger.warning(f"Could not detect specification from {xlsx_path}")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting specification: {e}")
            return None
    
    def extract_user_supported_bands_from_xlsx(self, xlsx_path: Path, spec_id: str) -> Optional[List[str]]:
        """
        Extract user's supported bands from PICS XLSX file
        
        Args:
            xlsx_path: Path to PICS XLSX file
            spec_id: Specification ID
            
        Returns:
            List of supported band names or None
        """
        try:
            # Look for PICS sheet
            xl_file = pd.ExcelFile(xlsx_path)
            pics_sheet = None
            
            for sheet_name in xl_file.sheet_names:
                if "PICS" in sheet_name.upper():
                    pics_sheet = sheet_name
                    break
            
            if not pics_sheet:
                logger.warning("No PICS sheet found in XLSX file")
                return None
            
            # Read PICS data
            pics_df = pd.read_excel(xlsx_path, sheet_name=pics_sheet)
            
            # Extract supported bands (this is spec-specific logic)
            supported_bands = []
            
            if spec_id == "36521":
                # LTE bands: Look for Yes/True values in relevant columns
                for idx, row in pics_df.iterrows():
                    for col in pics_df.columns:
                        if ("band" in str(col).lower() or "Band" in str(col)) and str(row[col]).lower() in ['yes', 'true', '1']:
                            # Extract band name from column name
                            band_name = str(col).replace("Band ", "").replace("band ", "").strip()
                            if band_name:
                                supported_bands.append(band_name)
            
            elif spec_id == "34123":
                # GSM/UMTS: Look for FDDI, TDD, etc.
                for idx, row in pics_df.iterrows():
                    for col in pics_df.columns:
                        if str(row[col]).lower() in ['yes', 'true', '1']:
                            col_str = str(col).upper()
                            if "FDDI" in col_str or "TDD" in col_str:
                                supported_bands.append("FDDI")
                            elif "GSM" in col_str:
                                supported_bands.append("GSM")
            
            logger.info(f"Extracted {len(supported_bands)} supported bands from PICS")
            return list(set(supported_bands)) if supported_bands else None
            
        except Exception as e:
            logger.error(f"Error extracting supported bands: {e}")
            return None
    
    def generate_testplan_from_xlsx(self, 
                                   input_xlsx_path: Path, 
                                   spec_id: Optional[str] = None,
                                   user_supported_bands: Optional[List[str]] = None) -> Path:
        """
        Generate test plan from XLSX input
        
        Args:
            input_xlsx_path: Path to input PICS XLSX file
            spec_id: Optional specification ID (auto-detected if None)
            user_supported_bands: Optional user supported bands (extracted if None)
            
        Returns:
            Path to generated test plan XLSX file
        """
        try:
            # Auto-detect specification if not provided
            if not spec_id:
                spec_id = self.detect_specification_from_xlsx(input_xlsx_path)
                if not spec_id:
                    raise ValueError("Could not detect 3GPP specification from input file")
            
            logger.info(f"Generating test plan for specification: {spec_id}")
            
            # Extract supported bands if not provided
            if not user_supported_bands:
                user_supported_bands = self.extract_user_supported_bands_from_xlsx(input_xlsx_path, spec_id)
            
            # Generate test plan using the engine
            with TestPlanEngine() as engine:
                test_plan_df = engine.generate_testplan_fast(
                    spec_id=spec_id,
                    user_supported_bands=user_supported_bands,
                    output_format="pandas"
                )
                
                # Generate output filename
                timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
                total_combinations = len(test_plan_df)
                unique_tests = test_plan_df['Test Case Name'].nunique()
                
                # Calculate coverage percentage (placeholder logic)
                coverage_pct = 100.0 if total_combinations > 0 else 0.0
                
                output_filename = f"PDX-256_All_{timestamp}_{coverage_pct:.2f}%.xlsx"
                output_path = self.temp_dir / output_filename
                
                # Write to Excel with specification sheet name
                sheet_name = f"3GPP TS {spec_id}-1"
                test_plan_df.to_excel(output_path, index=False, sheet_name=sheet_name)
                
                logger.info(f"Generated test plan: {total_combinations} combinations, {unique_tests} unique tests")
                logger.info(f"Output file: {output_path}")
                
                return output_path
                
        except Exception as e:
            logger.error(f"Error generating test plan: {e}")
            raise HTTPException(status_code=500, detail=f"Test plan generation failed: {str(e)}")


# Global generator instance
generator = TestPlanGenerator()


@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "3GPP TestPlan Generation Service",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/specifications")
async def get_available_specifications():
    """Get all available specifications in the database"""
    try:
        with TestPlanEngine() as engine:
            specs_df = engine.get_available_specifications()
            specs = specs_df.to_dicts()
            return {
                "specifications": specs,
                "total": len(specs)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get specifications: {str(e)}")


@app.get("/specifications/{spec_id}/coverage")
async def get_specification_coverage(spec_id: str):
    """Get coverage analysis for a specification"""
    try:
        with TestPlanEngine() as engine:
            analysis = engine.analyze_specification_coverage(spec_id)
            return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze coverage: {str(e)}")


@app.get("/specifications/{spec_id}/bands")
async def get_supported_bands(spec_id: str):
    """Get supported bands for a specification"""
    try:
        with TestPlanEngine() as engine:
            bands_df = engine.get_supported_bands(spec_id)
            bands = bands_df.to_dicts()
            return {
                "spec_id": spec_id,
                "bands": bands,
                "total": len(bands)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bands: {str(e)}")


@app.post("/generate-testplan")
async def generate_testplan(
    file: UploadFile = File(...),
    spec_id: Optional[str] = None,
    user_supported_bands: Optional[str] = None  # JSON string of band list
):
    """
    Generate test plan from uploaded PICS XLSX file
    
    Args:
        file: PICS XLSX file upload
        spec_id: Optional specification ID (auto-detected if not provided)
        user_supported_bands: Optional JSON string of supported bands
        
    Returns:
        Generated test plan XLSX file
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="File must be an Excel (.xlsx or .xls) file")
        
        # Save uploaded file
        upload_id = str(uuid.uuid4())
        temp_input_path = generator.temp_dir / f"input_{upload_id}_{file.filename}"
        
        with open(temp_input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse supported bands if provided
        bands_list = None
        if user_supported_bands:
            import json
            try:
                bands_list = json.loads(user_supported_bands)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for user_supported_bands")
        
        # Generate test plan
        output_path = generator.generate_testplan_from_xlsx(
            input_xlsx_path=temp_input_path,
            spec_id=spec_id,
            user_supported_bands=bands_list
        )
        
        # Clean up input file
        temp_input_path.unlink()
        
        # Return generated file
        return FileResponse(
            path=output_path,
            filename=output_path.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_testplan endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/generate-testplan-bulk")
async def generate_testplan_bulk(spec_ids: List[str]):
    """
    Generate test plans for multiple specifications in bulk
    
    Args:
        spec_ids: List of specification IDs to generate
        
    Returns:
        Results summary with download links
    """
    try:
        with TestPlanEngine() as engine:
            # Use temp directory for bulk generation
            output_dir = generator.temp_dir / "bulk_output"
            output_dir.mkdir(exist_ok=True)
            
            results = engine.bulk_generate_testplans(spec_ids, str(output_dir))
            
            # Add download links for successful generations
            for spec_id, result in results.items():
                if result['status'] == 'success':
                    result['download_url'] = f"/download/{Path(result['output_file']).name}"
            
            return {
                "results": results,
                "total_specs": len(spec_ids),
                "successful": len([r for r in results.values() if r['status'] == 'success']),
                "failed": len([r for r in results.values() if r['status'] == 'error'])
            }
            
    except Exception as e:
        logger.error(f"Error in bulk generation: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk generation failed: {str(e)}")


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated test plan file"""
    try:
        file_path = generator.temp_dir / "bulk_output" / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8105)