#!/usr/bin/env python3
"""
Time Series Analysis Processor
Advanced time series analysis with Prophet, ARIMA, seasonal decomposition, and forecasting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
import warnings
warnings.filterwarnings('ignore')

# Time series libraries - LAZY LOADING TO PREVENT MUTEX LOCKS
PROPHET_AVAILABLE = None
STATSMODELS_AVAILABLE = None  
SKLEARN_AVAILABLE = None

def _lazy_import_prophet():
    """Lazy import Prophet only when needed"""
    global PROPHET_AVAILABLE
    if PROPHET_AVAILABLE is None:
        try:
            from prophet import Prophet
            from prophet.diagnostics import cross_validation, performance_metrics
            PROPHET_AVAILABLE = True
            return {
                'Prophet': Prophet,
                'cross_validation': cross_validation,
                'performance_metrics': performance_metrics
            }
        except ImportError:
            PROPHET_AVAILABLE = False
            logging.warning("Prophet not available. Prophet forecasting will be disabled.")
            return None
    elif PROPHET_AVAILABLE:
        from prophet import Prophet
        from prophet.diagnostics import cross_validation, performance_metrics
        return {
            'Prophet': Prophet,
            'cross_validation': cross_validation,
            'performance_metrics': performance_metrics
        }
    else:
        return None

def _lazy_import_statsmodels():
    """Lazy import Statsmodels only when needed"""
    global STATSMODELS_AVAILABLE
    if STATSMODELS_AVAILABLE is None:
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.seasonal import seasonal_decompose
            from statsmodels.tsa.stattools import adfuller, kpss
            from statsmodels.tsa.api import ExponentialSmoothing
            from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
            STATSMODELS_AVAILABLE = True
            return {
                'ARIMA': ARIMA,
                'seasonal_decompose': seasonal_decompose,
                'adfuller': adfuller,
                'kpss': kpss,
                'ExponentialSmoothing': ExponentialSmoothing,
                'plot_acf': plot_acf,
                'plot_pacf': plot_pacf
            }
        except ImportError:
            STATSMODELS_AVAILABLE = False
            logging.warning("Statsmodels not available. ARIMA and statistical tests will be disabled.")
            return None
    elif STATSMODELS_AVAILABLE:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.seasonal import seasonal_decompose
        from statsmodels.tsa.stattools import adfuller, kpss
        from statsmodels.tsa.api import ExponentialSmoothing
        from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
        return {
            'ARIMA': ARIMA,
            'seasonal_decompose': seasonal_decompose,
            'adfuller': adfuller,
            'kpss': kpss,
            'ExponentialSmoothing': ExponentialSmoothing,
            'plot_acf': plot_acf,
            'plot_pacf': plot_pacf
        }
    else:
        return None

def _lazy_import_sklearn():
    """Lazy import sklearn metrics only when needed"""
    global SKLEARN_AVAILABLE
    if SKLEARN_AVAILABLE is None:
        try:
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            SKLEARN_AVAILABLE = True
            return {
                'mean_absolute_error': mean_absolute_error,
                'mean_squared_error': mean_squared_error,
                'r2_score': r2_score
            }
        except ImportError:
            SKLEARN_AVAILABLE = False
            return None
    elif SKLEARN_AVAILABLE:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        return {
            'mean_absolute_error': mean_absolute_error,
            'mean_squared_error': mean_squared_error,
            'r2_score': r2_score
        }
    else:
        return None

try:
    from ..preprocessors.csv_processor import CSVProcessor
except ImportError:
    # Fallback - create a minimal processor if needed
    class CSVProcessor:
        def __init__(self, file_path):
            self.file_path = file_path
            self.df = None
        def load_csv(self):
            return False

logger = logging.getLogger(__name__)

class TimeSeriesProcessor:
    """
    Comprehensive time series analysis processor
    Supports Prophet, ARIMA, seasonal decomposition, and advanced forecasting
    """
    
    def __init__(self, csv_processor: Optional[CSVProcessor] = None, file_path: Optional[str] = None):
        """
        Initialize time series processor
        
        Args:
            csv_processor: Existing CSVProcessor instance
            file_path: Path to CSV file (if csv_processor not provided)
        """
        if csv_processor:
            self.csv_processor = csv_processor
        elif file_path:
            self.csv_processor = CSVProcessor(file_path)
        else:
            raise ValueError("Either csv_processor or file_path must be provided")
        
        self.df = None
        self.time_series_data = {}
        self.models = {}
        self.forecasts = {}
        self.analysis_results = {}
        
        self._load_data()
    
    def _load_data(self) -> bool:
        """Load data from CSV processor"""
        try:
            if not self.csv_processor.load_csv():
                return False
            self.df = self.csv_processor.df.copy()
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def detect_time_series_columns(self) -> Dict[str, Any]:
        """
        Automatically detect potential time series data
        
        Returns:
            Dictionary with detected time columns and numeric columns for analysis
        """
        try:
            detection_results = {
                "time_columns": [],
                "numeric_columns": [],
                "potential_time_series": [],
                "recommendations": []
            }
            
            if self.df is None:
                return {"error": "No data loaded"}
            
            # Detect datetime columns
            for col in self.df.columns:
                # Check if column is already datetime
                if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                    detection_results["time_columns"].append({
                        "column": col,
                        "type": "datetime",
                        "confidence": "high"
                    })
                    continue
                
                # Check if column name suggests it's a date/time
                time_keywords = ['date', 'time', 'timestamp', 'created', 'updated', 'year', 'month', 'day']
                if any(keyword in col.lower() for keyword in time_keywords):
                    # Try to parse as datetime
                    try:
                        parsed = pd.to_datetime(self.df[col], errors='coerce')
                        null_ratio = parsed.isnull().sum() / len(parsed)
                        
                        if null_ratio < 0.1:  # Less than 10% failed to parse
                            detection_results["time_columns"].append({
                                "column": col,
                                "type": "parseable_datetime",
                                "confidence": "high" if null_ratio < 0.01 else "medium",
                                "null_ratio": round(null_ratio, 3)
                            })
                    except Exception:
                        pass
            
            # Detect numeric columns suitable for time series analysis
            numeric_columns = self.df.select_dtypes(include=[np.number]).columns
            for col in numeric_columns:
                if self.df[col].notna().sum() > 10:  # At least 10 non-null values
                    detection_results["numeric_columns"].append({
                        "column": col,
                        "non_null_count": int(self.df[col].notna().sum()),
                        "variance": float(self.df[col].var()) if self.df[col].var() is not np.nan else 0
                    })
            
            # Suggest potential time series combinations
            if detection_results["time_columns"] and detection_results["numeric_columns"]:
                for time_col in detection_results["time_columns"]:
                    for numeric_col in detection_results["numeric_columns"]:
                        detection_results["potential_time_series"].append({
                            "time_column": time_col["column"],
                            "value_column": numeric_col["column"],
                            "confidence": time_col["confidence"]
                        })
            
            # Generate recommendations
            if not detection_results["time_columns"]:
                detection_results["recommendations"].append(
                    "No time columns detected. Consider adding a date/time column or check column naming."
                )
            elif not detection_results["numeric_columns"]:
                detection_results["recommendations"].append(
                    "No suitable numeric columns found for time series analysis."
                )
            else:
                detection_results["recommendations"].append(
                    f"Found {len(detection_results['time_columns'])} time column(s) and "
                    f"{len(detection_results['numeric_columns'])} numeric column(s). "
                    f"Ready for time series analysis."
                )
            
            return detection_results
            
        except Exception as e:
            logger.error(f"Error detecting time series columns: {e}")
            return {"error": str(e)}
    
    def prepare_time_series(self, time_column: str, value_column: str, 
                          freq: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare time series data for analysis
        
        Args:
            time_column: Column containing time/date information
            value_column: Column containing the values to analyze
            freq: Frequency of the time series (auto-detected if None)
            
        Returns:
            Prepared time series data and metadata
        """
        try:
            if self.df is None:
                return {"error": "No data loaded"}
            
            if time_column not in self.df.columns:
                return {"error": f"Time column '{time_column}' not found"}
            
            if value_column not in self.df.columns:
                return {"error": f"Value column '{value_column}' not found"}
            
            # Create working copy
            ts_df = self.df[[time_column, value_column]].copy()
            
            # Convert time column to datetime
            if not pd.api.types.is_datetime64_any_dtype(ts_df[time_column]):
                ts_df[time_column] = pd.to_datetime(ts_df[time_column], errors='coerce')
            
            # Remove rows with invalid dates or values
            initial_count = len(ts_df)
            ts_df = ts_df.dropna()
            cleaned_count = len(ts_df)
            
            if cleaned_count == 0:
                return {"error": "No valid time series data after cleaning"}
            
            # Sort by time
            ts_df = ts_df.sort_values(by=time_column).reset_index(drop=True)
            
            # Rename columns for consistency
            ts_df.columns = ['ds', 'y']  # Prophet naming convention
            
            # Auto-detect frequency if not provided
            if freq is None and len(ts_df) > 1:
                time_diffs = ts_df['ds'].diff().dropna()
                most_common_diff = time_diffs.mode()
                
                if len(most_common_diff) > 0:
                    diff_days = most_common_diff.iloc[0].days
                    diff_seconds = most_common_diff.iloc[0].total_seconds()
                    
                    if diff_seconds <= 3600:  # Hourly or less
                        freq = 'H'
                    elif diff_days == 1:
                        freq = 'D'
                    elif diff_days == 7:
                        freq = 'W'
                    elif 28 <= diff_days <= 31:
                        freq = 'M'
                    elif 365 <= diff_days <= 366:
                        freq = 'Y'
                    else:
                        freq = 'D'  # Default
            
            # Basic statistics
            stats = {
                "count": len(ts_df),
                "start_date": ts_df['ds'].min().isoformat(),
                "end_date": ts_df['ds'].max().isoformat(),
                "duration_days": (ts_df['ds'].max() - ts_df['ds'].min()).days,
                "mean": float(ts_df['y'].mean()),
                "std": float(ts_df['y'].std()),
                "min": float(ts_df['y'].min()),
                "max": float(ts_df['y'].max()),
                "frequency": freq,
                "missing_data_removed": initial_count - cleaned_count
            }
            
            # Store prepared data
            series_key = f"{time_column}_{value_column}"
            self.time_series_data[series_key] = {
                "data": ts_df,
                "metadata": {
                    "time_column": time_column,
                    "value_column": value_column,
                    "frequency": freq,
                    "statistics": stats
                }
            }
            
            result = {
                "success": True,
                "series_key": series_key,
                "statistics": stats,
                "data_preview": ts_df.head(10).to_dict('records'),
                "frequency": freq
            }
            
            logger.info(f"Time series prepared: {cleaned_count} points from {stats['start_date']} to {stats['end_date']}")
            return result
            
        except Exception as e:
            logger.error(f"Error preparing time series: {e}")
            return {"error": str(e)}
    
    def analyze_stationarity(self, series_key: str) -> Dict[str, Any]:
        """
        Analyze stationarity of time series using statistical tests
        
        Args:
            series_key: Key identifying the time series data
            
        Returns:
            Stationarity analysis results
        """
        try:
            if not STATSMODELS_AVAILABLE:
                return {"error": "Statsmodels not available for stationarity tests"}
            
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"]
            series = ts_data['y']
            
            stationarity_results = {
                "tests": {},
                "interpretation": {},
                "recommendations": []
            }
            
            # Augmented Dickey-Fuller test
            try:
                adf_result = adfuller(series.dropna())
                stationarity_results["tests"]["adf"] = {
                    "test_statistic": float(adf_result[0]),
                    "p_value": float(adf_result[1]),
                    "critical_values": {str(k): float(v) for k, v in adf_result[4].items()},
                    "is_stationary": adf_result[1] < 0.05
                }
            except Exception as e:
                logger.warning(f"ADF test failed: {e}")
            
            # KPSS test
            try:
                kpss_result = kpss(series.dropna())
                stationarity_results["tests"]["kpss"] = {
                    "test_statistic": float(kpss_result[0]),
                    "p_value": float(kpss_result[1]),
                    "critical_values": {str(k): float(v) for k, v in kpss_result[3].items()},
                    "is_stationary": kpss_result[1] > 0.05
                }
            except Exception as e:
                logger.warning(f"KPSS test failed: {e}")
            
            # Overall interpretation
            adf_stationary = stationarity_results["tests"].get("adf", {}).get("is_stationary", False)
            kpss_stationary = stationarity_results["tests"].get("kpss", {}).get("is_stationary", False)
            
            if adf_stationary and kpss_stationary:
                stationarity_results["interpretation"]["conclusion"] = "Series appears to be stationary"
                stationarity_results["interpretation"]["confidence"] = "high"
            elif adf_stationary or kpss_stationary:
                stationarity_results["interpretation"]["conclusion"] = "Series stationarity is uncertain"
                stationarity_results["interpretation"]["confidence"] = "medium"
            else:
                stationarity_results["interpretation"]["conclusion"] = "Series appears to be non-stationary"
                stationarity_results["interpretation"]["confidence"] = "high"
            
            # Recommendations
            if not (adf_stationary and kpss_stationary):
                stationarity_results["recommendations"].extend([
                    "Consider differencing the series to achieve stationarity",
                    "Try log transformation if series shows exponential growth",
                    "Remove trend and seasonal components before ARIMA modeling"
                ])
            else:
                stationarity_results["recommendations"].append(
                    "Series is stationary - suitable for ARIMA modeling"
                )
            
            return stationarity_results
            
        except Exception as e:
            logger.error(f"Error analyzing stationarity: {e}")
            return {"error": str(e)}
    
    def detect_seasonality(self, series_key: str) -> Dict[str, Any]:
        """
        Detect seasonal patterns in the time series
        
        Args:
            series_key: Key identifying the time series data
            
        Returns:
            Seasonality detection results
        """
        try:
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"]
            series = ts_data['y']
            
            # Basic seasonality detection using autocorrelation
            seasonality_results = {
                "has_seasonality": False,
                "seasonal_periods": [],
                "strength": 0.0,
                "confidence": "low"
            }
            
            if len(series) < 24:  # Need at least 24 points for meaningful analysis
                seasonality_results["error"] = "Insufficient data for seasonality detection"
                return seasonality_results
            
            # Test common seasonal periods based on frequency
            freq = self.time_series_data[series_key]["metadata"]["frequency"]
            test_periods = []
            
            if freq == 'H':  # Hourly data
                test_periods = [24, 168]  # Daily, weekly
            elif freq == 'D':  # Daily data  
                test_periods = [7, 30, 365]  # Weekly, monthly, yearly
            elif freq == 'W':  # Weekly data
                test_periods = [52]  # Yearly
            elif freq == 'M':  # Monthly data
                test_periods = [12]  # Yearly
            else:
                test_periods = [7, 12, 24]  # Default periods to test
            
            max_autocorr = 0
            best_period = None
            
            for period in test_periods:
                if len(series) > 2 * period:  # Need at least 2 cycles
                    try:
                        # Calculate autocorrelation at lag = period
                        autocorr = series.autocorr(lag=period)
                        if not np.isnan(autocorr) and abs(autocorr) > max_autocorr:
                            max_autocorr = abs(autocorr)
                            best_period = period
                            seasonality_results["seasonal_periods"].append({
                                "period": period,
                                "autocorrelation": float(autocorr),
                                "strength": float(abs(autocorr))
                            })
                    except Exception:
                        continue
            
            # Determine if seasonality exists
            if max_autocorr > 0.3:  # Strong seasonality
                seasonality_results["has_seasonality"] = True
                seasonality_results["strength"] = float(max_autocorr)
                seasonality_results["confidence"] = "high" if max_autocorr > 0.6 else "medium"
            elif max_autocorr > 0.1:  # Weak seasonality
                seasonality_results["has_seasonality"] = True
                seasonality_results["strength"] = float(max_autocorr)
                seasonality_results["confidence"] = "low"
            
            if best_period:
                seasonality_results["dominant_period"] = best_period
            
            return seasonality_results
            
        except Exception as e:
            logger.error(f"Error detecting seasonality: {e}")
            return {"error": str(e)}
    
    def seasonal_decomposition(self, series_key: str, period: Optional[int] = None,
                             model: str = 'additive') -> Dict[str, Any]:
        """
        Perform seasonal decomposition of time series
        
        Args:
            series_key: Key identifying the time series data
            period: Seasonal period (auto-detected if None)
            model: 'additive' or 'multiplicative'
            
        Returns:
            Seasonal decomposition results
        """
        try:
            if not STATSMODELS_AVAILABLE:
                return {"error": "Statsmodels not available for seasonal decomposition"}
            
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"]
            series = ts_data.set_index('ds')['y']
            
            # Auto-detect period if not provided
            if period is None:
                freq = self.time_series_data[series_key]["metadata"]["frequency"]
                if freq == 'D':
                    period = 365  # Daily data - yearly seasonality
                elif freq == 'W':
                    period = 52   # Weekly data - yearly seasonality
                elif freq == 'M':
                    period = 12   # Monthly data - yearly seasonality
                elif freq == 'H':
                    period = 24   # Hourly data - daily seasonality
                else:
                    period = min(len(series) // 2, 365)  # Default
            
            # Ensure we have enough data points
            if len(series) < 2 * period:
                return {"error": f"Not enough data for seasonal decomposition (need at least {2 * period} points)"}
            
            # Perform decomposition
            decomposition = seasonal_decompose(series, model=model, period=period)
            
            # Extract components
            decomp_results = {
                "model": model,
                "period": period,
                "components": {
                    "trend": decomposition.trend.dropna().to_dict(),
                    "seasonal": decomposition.seasonal.to_dict(),
                    "residual": decomposition.resid.dropna().to_dict()
                },
                "statistics": {},
                "insights": []
            }
            
            # Calculate statistics for each component
            for component_name, component_data in [
                ("trend", decomposition.trend.dropna()),
                ("seasonal", decomposition.seasonal),
                ("residual", decomposition.resid.dropna())
            ]:
                if len(component_data) > 0:
                    decomp_results["statistics"][component_name] = {
                        "mean": float(component_data.mean()),
                        "std": float(component_data.std()),
                        "min": float(component_data.min()),
                        "max": float(component_data.max()),
                        "variance_explained": float(component_data.var() / series.var() * 100)
                    }
            
            # Generate insights
            seasonal_strength = decomposition.seasonal.std() / series.std()
            trend_strength = decomposition.trend.dropna().std() / series.std()
            
            if seasonal_strength > 0.1:
                decomp_results["insights"].append(f"Strong seasonal pattern detected (strength: {seasonal_strength:.2f})")
            
            if trend_strength > 0.1:
                decomp_results["insights"].append(f"Significant trend component (strength: {trend_strength:.2f})")
            
            # Residual analysis
            residual_std = decomposition.resid.dropna().std()
            if residual_std / series.std() < 0.3:
                decomp_results["insights"].append("Decomposition explains most of the variance in the series")
            else:
                decomp_results["insights"].append("Significant unexplained variance remains in residuals")
            
            return decomp_results
            
        except Exception as e:
            logger.error(f"Error in seasonal decomposition: {e}")
            return {"error": str(e)}
    
    def prophet_forecast(self, series_key: str, periods: int = 30, 
                        include_holidays: bool = False,
                        seasonality_mode: str = 'additive',
                        daily_seasonality: bool = 'auto',
                        weekly_seasonality: bool = 'auto',
                        yearly_seasonality: bool = 'auto') -> Dict[str, Any]:
        """
        Generate forecast using Prophet
        
        Args:
            series_key: Key identifying the time series data
            periods: Number of periods to forecast
            include_holidays: Whether to include holiday effects
            seasonality_mode: 'additive' or 'multiplicative'
            daily_seasonality: Enable daily seasonality
            weekly_seasonality: Enable weekly seasonality  
            yearly_seasonality: Enable yearly seasonality
            
        Returns:
            Prophet forecast results
        """
        try:
            if not PROPHET_AVAILABLE:
                return {"error": "Prophet not available for forecasting"}
            
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"].copy()
            
            # Initialize Prophet model
            model = Prophet(
                seasonality_mode=seasonality_mode,
                daily_seasonality=daily_seasonality,
                weekly_seasonality=weekly_seasonality,
                yearly_seasonality=yearly_seasonality
            )
            
            # Add country holidays if requested
            if include_holidays:
                try:
                    model.add_country_holidays(country_name='US')
                except Exception:
                    logger.warning("Could not add US holidays to Prophet model")
            
            # Fit model
            model.fit(ts_data)
            
            # Create future dataframe
            future = model.make_future_dataframe(periods=periods)
            
            # Generate forecast
            forecast = model.predict(future)
            
            # Extract forecast results
            forecast_data = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
            
            # Calculate performance metrics on historical data
            historical_forecast = forecast.iloc[:-periods]
            historical_actual = ts_data['y'].values
            historical_predicted = historical_forecast['yhat'].values
            
            if SKLEARN_AVAILABLE and len(historical_actual) == len(historical_predicted):
                performance = {
                    "mae": float(mean_absolute_error(historical_actual, historical_predicted)),
                    "mse": float(mean_squared_error(historical_actual, historical_predicted)),
                    "rmse": float(np.sqrt(mean_squared_error(historical_actual, historical_predicted))),
                    "r2": float(r2_score(historical_actual, historical_predicted))
                }
            else:
                performance = {"error": "Could not calculate performance metrics"}
            
            # Store model and results
            model_key = f"{series_key}_prophet"
            self.models[model_key] = model
            self.forecasts[model_key] = forecast
            
            results = {
                "model_type": "prophet",
                "model_key": model_key,
                "forecast_periods": periods,
                "forecast_data": forecast_data.to_dict('records'),
                "performance_metrics": performance,
                "seasonality_mode": seasonality_mode,
                "model_components": {
                    "trend": forecast['trend'].iloc[-periods:].to_dict(),
                    "weekly": forecast.get('weekly', pd.Series()).iloc[-periods:].to_dict() if 'weekly' in forecast else {},
                    "yearly": forecast.get('yearly', pd.Series()).iloc[-periods:].to_dict() if 'yearly' in forecast else {}
                },
                "uncertainty_intervals": {
                    "yhat_lower": forecast_data['yhat_lower'].tolist(),
                    "yhat_upper": forecast_data['yhat_upper'].tolist()
                }
            }
            
            logger.info(f"Prophet forecast completed: {periods} periods")
            return results
            
        except Exception as e:
            logger.error(f"Error in Prophet forecasting: {e}")
            return {"error": str(e)}
    
    def arima_forecast(self, series_key: str, periods: int = 30,
                      order: Optional[Tuple[int, int, int]] = None,
                      seasonal_order: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Generate forecast using ARIMA
        
        Args:
            series_key: Key identifying the time series data
            periods: Number of periods to forecast
            order: ARIMA order (p, d, q) - auto-selected if None
            seasonal_order: Seasonal ARIMA order (P, D, Q, s) - auto-selected if None
            
        Returns:
            ARIMA forecast results
        """
        try:
            if not STATSMODELS_AVAILABLE:
                return {"error": "Statsmodels not available for ARIMA forecasting"}
            
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"]
            series = ts_data['y']
            
            # Auto-select ARIMA order if not provided
            if order is None:
                # Simple heuristic for ARIMA order selection
                # In practice, you might want to use auto_arima from pmdarima
                order = (1, 1, 1)  # Default order
            
            # Fit ARIMA model
            model = ARIMA(series, order=order, seasonal_order=seasonal_order)
            fitted_model = model.fit()
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=periods)
            forecast_ci = fitted_model.get_forecast(steps=periods).conf_int()
            
            # Calculate performance metrics (in-sample)
            fitted_values = fitted_model.fittedvalues
            residuals = fitted_model.resid
            
            if SKLEARN_AVAILABLE:
                # Use overlapping indices for performance calculation
                actual_values = series.iloc[len(series) - len(fitted_values):]
                performance = {
                    "aic": float(fitted_model.aic),
                    "bic": float(fitted_model.bic),
                    "mae": float(mean_absolute_error(actual_values, fitted_values)),
                    "mse": float(mean_squared_error(actual_values, fitted_values)),
                    "rmse": float(np.sqrt(mean_squared_error(actual_values, fitted_values)))
                }
            else:
                performance = {
                    "aic": float(fitted_model.aic),
                    "bic": float(fitted_model.bic)
                }
            
            # Store model
            model_key = f"{series_key}_arima"
            self.models[model_key] = fitted_model
            
            results = {
                "model_type": "arima",
                "model_key": model_key,
                "order": order,
                "seasonal_order": seasonal_order,
                "forecast_periods": periods,
                "forecast_values": forecast_result.tolist(),
                "confidence_intervals": {
                    "lower": forecast_ci.iloc[:, 0].tolist(),
                    "upper": forecast_ci.iloc[:, 1].tolist()
                },
                "performance_metrics": performance,
                "model_summary": {
                    "aic": float(fitted_model.aic),
                    "bic": float(fitted_model.bic),
                    "log_likelihood": float(fitted_model.llf)
                }
            }
            
            logger.info(f"ARIMA forecast completed: {periods} periods")
            return results
            
        except Exception as e:
            logger.error(f"Error in ARIMA forecasting: {e}")
            return {"error": str(e)}
    
    def exponential_smoothing_forecast(self, series_key: str, periods: int = 30,
                                     trend: Optional[str] = None,
                                     seasonal: Optional[str] = None,
                                     seasonal_periods: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate forecast using Exponential Smoothing
        
        Args:
            series_key: Key identifying the time series data
            periods: Number of periods to forecast
            trend: Trend component ('add', 'mul', or None)
            seasonal: Seasonal component ('add', 'mul', or None)
            seasonal_periods: Number of periods in seasonal cycle
            
        Returns:
            Exponential Smoothing forecast results
        """
        try:
            if not STATSMODELS_AVAILABLE:
                return {"error": "Statsmodels not available for Exponential Smoothing"}
            
            if series_key not in self.time_series_data:
                return {"error": f"Time series '{series_key}' not found"}
            
            ts_data = self.time_series_data[series_key]["data"]
            series = ts_data['y']
            
            # Auto-detect parameters if not provided
            if seasonal_periods is None:
                freq = self.time_series_data[series_key]["metadata"]["frequency"]
                if freq == 'D':
                    seasonal_periods = 7  # Weekly seasonality for daily data
                elif freq == 'M':
                    seasonal_periods = 12  # Yearly seasonality for monthly data
                else:
                    seasonal_periods = None
            
            # Fit Exponential Smoothing model
            model = ExponentialSmoothing(
                series,
                trend=trend,
                seasonal=seasonal,
                seasonal_periods=seasonal_periods
            )
            fitted_model = model.fit()
            
            # Generate forecast
            forecast_result = fitted_model.forecast(steps=periods)
            
            # Calculate performance metrics (in-sample)
            fitted_values = fitted_model.fittedvalues
            
            if SKLEARN_AVAILABLE and len(fitted_values) > 0:
                # Align actual and fitted values
                actual_values = series.iloc[len(series) - len(fitted_values):]
                performance = {
                    "mae": float(mean_absolute_error(actual_values, fitted_values)),
                    "mse": float(mean_squared_error(actual_values, fitted_values)),
                    "rmse": float(np.sqrt(mean_squared_error(actual_values, fitted_values)))
                }
            else:
                performance = {}
            
            # Store model
            model_key = f"{series_key}_exp_smoothing"
            self.models[model_key] = fitted_model
            
            results = {
                "model_type": "exponential_smoothing",
                "model_key": model_key,
                "trend": trend,
                "seasonal": seasonal,
                "seasonal_periods": seasonal_periods,
                "forecast_periods": periods,
                "forecast_values": forecast_result.tolist(),
                "performance_metrics": performance,
                "model_parameters": {
                    "alpha": float(fitted_model.params.get('smoothing_level', 0)),
                    "beta": float(fitted_model.params.get('smoothing_trend', 0)) if trend else None,
                    "gamma": float(fitted_model.params.get('smoothing_seasonal', 0)) if seasonal else None
                }
            }
            
            logger.info(f"Exponential Smoothing forecast completed: {periods} periods")
            return results
            
        except Exception as e:
            logger.error(f"Error in Exponential Smoothing forecasting: {e}")
            return {"error": str(e)}
    
    def comprehensive_time_series_analysis(self, time_column: str, value_column: str,
                                         forecast_periods: int = 30) -> Dict[str, Any]:
        """
        Perform comprehensive time series analysis with all available methods
        
        Args:
            time_column: Column containing time/date information
            value_column: Column containing the values to analyze
            forecast_periods: Number of periods to forecast
            
        Returns:
            Complete time series analysis results
        """
        try:
            analysis_results = {
                "data_preparation": {},
                "stationarity_analysis": {},
                "seasonal_decomposition": {},
                "forecasting_models": {},
                "model_comparison": {},
                "recommendations": []
            }
            
            # 1. Prepare time series data
            logger.info("Preparing time series data...")
            prep_result = self.prepare_time_series(time_column, value_column)
            analysis_results["data_preparation"] = prep_result
            
            if not prep_result.get("success"):
                return analysis_results
            
            series_key = prep_result["series_key"]
            
            # 2. Stationarity analysis
            logger.info("Analyzing stationarity...")
            stationarity_result = self.analyze_stationarity(series_key)
            analysis_results["stationarity_analysis"] = stationarity_result
            
            # 3. Seasonal decomposition
            logger.info("Performing seasonal decomposition...")
            decomp_result = self.seasonal_decomposition(series_key)
            analysis_results["seasonal_decomposition"] = decomp_result
            
            # 4. Forecasting with multiple models
            models_to_try = []
            
            # Prophet (if available)
            if PROPHET_AVAILABLE:
                models_to_try.append("prophet")
            
            # ARIMA (if available and data seems suitable)
            if STATSMODELS_AVAILABLE:
                models_to_try.extend(["arima", "exponential_smoothing"])
            
            forecasting_results = {}
            for model_type in models_to_try:
                try:
                    logger.info(f"Running {model_type} forecast...")
                    
                    if model_type == "prophet":
                        result = self.prophet_forecast(series_key, forecast_periods)
                    elif model_type == "arima":
                        result = self.arima_forecast(series_key, forecast_periods)
                    elif model_type == "exponential_smoothing":
                        result = self.exponential_smoothing_forecast(series_key, forecast_periods)
                    
                    if "error" not in result:
                        forecasting_results[model_type] = result
                    else:
                        logger.warning(f"{model_type} forecasting failed: {result['error']}")
                        
                except Exception as e:
                    logger.warning(f"Error with {model_type} forecasting: {e}")
            
            analysis_results["forecasting_models"] = forecasting_results
            
            # 5. Model comparison
            if len(forecasting_results) > 1:
                comparison = self._compare_forecast_models(forecasting_results)
                analysis_results["model_comparison"] = comparison
            
            # 6. Generate recommendations
            recommendations = self._generate_time_series_recommendations(analysis_results)
            analysis_results["recommendations"] = recommendations
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive time series analysis: {e}")
            return {"error": str(e)}
    
    def _compare_forecast_models(self, forecasting_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance of different forecasting models"""
        try:
            comparison = {
                "model_rankings": [],
                "best_model": None,
                "performance_summary": {}
            }
            
            model_performances = []
            
            for model_name, result in forecasting_results.items():
                performance = result.get("performance_metrics", {})
                
                if "mae" in performance:
                    model_performances.append({
                        "model": model_name,
                        "mae": performance["mae"],
                        "rmse": performance.get("rmse", float('inf')),
                        "r2": performance.get("r2", 0)
                    })
            
            # Rank by MAE (lower is better)
            model_performances.sort(key=lambda x: x["mae"])
            
            comparison["model_rankings"] = model_performances
            
            if model_performances:
                comparison["best_model"] = model_performances[0]["model"]
                
                best_mae = model_performances[0]["mae"]
                worst_mae = model_performances[-1]["mae"] if len(model_performances) > 1 else best_mae
                
                comparison["performance_summary"] = {
                    "best_mae": best_mae,
                    "worst_mae": worst_mae,
                    "performance_gap": (worst_mae - best_mae) / best_mae * 100 if best_mae > 0 else 0
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing forecast models: {e}")
            return {"error": str(e)}
    
    def _generate_time_series_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on time series analysis"""
        recommendations = []
        
        try:
            # Data quality recommendations
            prep_result = analysis_results.get("data_preparation", {})
            if prep_result.get("statistics", {}).get("missing_data_removed", 0) > 0:
                removed_count = prep_result["statistics"]["missing_data_removed"]
                recommendations.append(f"Data cleaning removed {removed_count} rows with missing values. Consider investigating data quality.")
            
            # Stationarity recommendations
            stationarity = analysis_results.get("stationarity_analysis", {})
            if stationarity.get("interpretation", {}).get("conclusion") == "Series appears to be non-stationary":
                recommendations.append("Series is non-stationary. Consider differencing or detrending before ARIMA modeling.")
            
            # Seasonality recommendations
            seasonal_decomp = analysis_results.get("seasonal_decomposition", {})
            if seasonal_decomp.get("insights"):
                recommendations.extend(seasonal_decomp["insights"])
            
            # Model selection recommendations
            model_comparison = analysis_results.get("model_comparison", {})
            if model_comparison.get("best_model"):
                best_model = model_comparison["best_model"]
                recommendations.append(f"Based on performance metrics, {best_model} provides the best forecasting accuracy.")
            
            # Forecasting recommendations
            forecasting_models = analysis_results.get("forecasting_models", {})
            if "prophet" in forecasting_models:
                recommendations.append("Prophet model successfully fitted - good for capturing trends and seasonality.")
            
            if not recommendations:
                recommendations.append("Time series analysis completed successfully. Consider extending forecast horizon for longer-term planning.")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Could not generate specific recommendations due to analysis errors.")
        
        return recommendations
    
    def get_model_results(self, model_key: Optional[str] = None) -> Dict[str, Any]:
        """Get results for specific model or all models"""
        if model_key:
            return {
                "model": self.models.get(model_key),
                "forecast": self.forecasts.get(model_key)
            }
        else:
            return {
                "models": list(self.models.keys()),
                "forecasts": list(self.forecasts.keys()),
                "time_series_data": list(self.time_series_data.keys())
            }

# Convenience functions
def analyze_time_series(file_path: str, time_column: str, value_column: str,
                       forecast_periods: int = 30) -> Dict[str, Any]:
    """
    Convenience function for comprehensive time series analysis
    
    Args:
        file_path: Path to data file
        time_column: Column containing time/date information
        value_column: Column containing values to analyze
        forecast_periods: Number of periods to forecast
        
    Returns:
        Complete time series analysis results
    """
    processor = TimeSeriesProcessor(file_path=file_path)
    return processor.comprehensive_time_series_analysis(time_column, value_column, forecast_periods)

def quick_prophet_forecast(file_path: str, time_column: str, value_column: str,
                          periods: int = 30) -> Dict[str, Any]:
    """
    Convenience function for quick Prophet forecasting
    
    Args:
        file_path: Path to data file
        time_column: Column containing time/date information
        value_column: Column containing values to analyze
        periods: Number of periods to forecast
        
    Returns:
        Prophet forecast results
    """
    processor = TimeSeriesProcessor(file_path=file_path)
    prep_result = processor.prepare_time_series(time_column, value_column)
    
    if prep_result.get("success"):
        return processor.prophet_forecast(prep_result["series_key"], periods)
    else:
        return prep_result