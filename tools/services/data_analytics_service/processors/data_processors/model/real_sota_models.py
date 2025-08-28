#!/usr/bin/env python3
"""
真实SOTA时间序列模型实现
基于实际可用的库实现TimeMixer、ModernTCN、MICN等模型
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# LAZY LOADING PyTorch to prevent mutex lock issues
def _import_torch():
    """Lazy import PyTorch modules"""
    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        return torch, nn, optim
    except ImportError:
        raise ImportError("PyTorch not available for SOTA models")

logger = logging.getLogger(__name__)

@dataclass
class RealModelPerformance:
    """真实模型性能指标"""
    model_name: str
    mae: float
    rmse: float
    mape: float
    r2: float
    training_time: float
    inference_time: float
    model_size: int
    convergence_epochs: int
    
    def get_composite_score(self) -> float:
        """计算综合评分"""
        # 归一化指标
        mae_score = max(0, 1 - min(self.mae / 100, 1))
        rmse_score = max(0, 1 - min(self.rmse / 150, 1))
        mape_score = max(0, 1 - min(self.mape / 100, 1))
        r2_score = max(0, min(self.r2, 1))
        
        # 考虑效率指标
        time_penalty = max(0, 1 - (self.training_time / 300))  # 5分钟内完成为满分
        
        composite_score = (
            0.3 * mae_score +
            0.3 * rmse_score + 
            0.2 * mape_score +
            0.15 * r2_score +
            0.05 * time_penalty
        )
        return round(composite_score, 4)

class RealTimeMixerModel(nn.Module):
    """真实TimeMixer模型实现"""
    
    def __init__(self, input_size=1, hidden_size=64, num_scales=3, seq_len=60):
        super(RealTimeMixerModel, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_scales = num_scales
        self.seq_len = seq_len
        
        # 多尺度卷积分支
        self.scale_convs = nn.ModuleList([
            nn.Conv1d(input_size, hidden_size, kernel_size=3+2*i, padding=1+i)
            for i in range(num_scales)
        ])
        
        # 季节性和趋势分解
        self.seasonal_proj = nn.Linear(hidden_size * num_scales, hidden_size)
        self.trend_proj = nn.Linear(hidden_size * num_scales, hidden_size)
        
        # 混合层
        self.mixer = nn.Linear(hidden_size * 2, hidden_size)
        self.output_proj = nn.Linear(hidden_size, 1)
        
        # Dropout和激活
        self.dropout = nn.Dropout(0.1)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        x = x.transpose(1, 2)  # (batch, features, seq_len)
        
        # 多尺度特征提取
        scale_features = []
        for conv in self.scale_convs:
            scale_feat = self.relu(conv(x))
            scale_features.append(scale_feat.mean(dim=2))  # Global average pooling
        
        # 拼接多尺度特征
        combined_features = torch.cat(scale_features, dim=1)
        
        # 分解为季节性和趋势
        seasonal = self.relu(self.seasonal_proj(combined_features))
        trend = self.relu(self.trend_proj(combined_features))
        
        # 混合特征
        mixed = self.mixer(torch.cat([seasonal, trend], dim=1))
        mixed = self.dropout(mixed)
        
        # 输出预测
        output = self.output_proj(mixed)
        return output

class RealModernTCNModel(nn.Module):
    """真实ModernTCN模型实现"""
    
    def __init__(self, input_size=1, hidden_size=64, num_layers=4, kernel_size=3, dropout=0.1):
        super(RealModernTCNModel, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # Temporal Block构建
        self.tcn_blocks = nn.ModuleList()
        dilation = 1
        
        for i in range(num_layers):
            in_channels = input_size if i == 0 else hidden_size
            self.tcn_blocks.append(
                TemporalBlock(in_channels, hidden_size, kernel_size, dilation, dropout)
            )
            dilation *= 2
        
        # 输出层
        self.output_proj = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        x = x.transpose(1, 2)  # (batch, features, seq_len)
        
        # 通过TCN blocks
        for tcn_block in self.tcn_blocks:
            x = tcn_block(x)
        
        # 取最后时间步的输出
        x = x[:, :, -1]  # (batch, hidden_size)
        output = self.output_proj(x)
        return output

class TemporalBlock(nn.Module):
    """TCN的时间块"""
    
    def __init__(self, in_channels, out_channels, kernel_size, dilation, dropout):
        super(TemporalBlock, self).__init__()
        
        # 因果卷积
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, 
                              dilation=dilation, padding=(kernel_size-1)*dilation)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size,
                              dilation=dilation, padding=(kernel_size-1)*dilation)
        
        # 批归一化和激活
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
        # 残差连接
        self.residual = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        
    def forward(self, x):
        # 因果卷积确保不泄露未来信息
        residual = x
        
        # 第一个卷积块
        out = self.conv1(x)
        out = out[:, :, :x.size(2)]  # 裁剪到原始长度
        out = self.relu(self.bn1(out))
        out = self.dropout(out)
        
        # 第二个卷积块  
        out = self.conv2(out)
        out = out[:, :, :x.size(2)]  # 裁剪到原始长度
        out = self.relu(self.bn2(out))
        out = self.dropout(out)
        
        # 残差连接
        if self.residual is not None:
            residual = self.residual(residual)
        
        return self.relu(out + residual)

class RealMICNModel(nn.Module):
    """真实MICN模型实现"""
    
    def __init__(self, input_size=1, hidden_size=64, seq_len=60):
        super(RealMICNModel, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.seq_len = seq_len
        
        # Multi-scale Inception模块
        self.inception_1x1 = nn.Conv1d(input_size, hidden_size//4, 1)
        self.inception_3x3 = nn.Conv1d(input_size, hidden_size//4, 3, padding=1)
        self.inception_5x5 = nn.Conv1d(input_size, hidden_size//4, 5, padding=2)
        self.inception_pool = nn.Sequential(
            nn.MaxPool1d(3, stride=1, padding=1),
            nn.Conv1d(input_size, hidden_size//4, 1)
        )
        
        # 全局和局部特征融合
        self.global_conv = nn.Conv1d(hidden_size, hidden_size, kernel_size=seq_len)
        self.local_conv = nn.Conv1d(hidden_size, hidden_size, kernel_size=3, padding=1)
        
        # 输出层
        self.output_proj = nn.Linear(hidden_size * 2, 1)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        x = x.transpose(1, 2)  # (batch, features, seq_len)
        
        # Multi-scale Inception
        inception_1x1 = self.relu(self.inception_1x1(x))
        inception_3x3 = self.relu(self.inception_3x3(x))
        inception_5x5 = self.relu(self.inception_5x5(x))
        inception_pool = self.relu(self.inception_pool(x))
        
        # 拼接所有inception分支
        inception_out = torch.cat([inception_1x1, inception_3x3, inception_5x5, inception_pool], dim=1)
        
        # 全局和局部特征
        global_feat = self.global_conv(inception_out).squeeze(-1)  # (batch, hidden_size)
        local_feat = self.local_conv(inception_out).mean(dim=2)    # (batch, hidden_size)
        
        # 特征融合
        combined = torch.cat([global_feat, local_feat], dim=1)
        combined = self.dropout(combined)
        
        # 输出预测
        output = self.output_proj(combined)
        return output

class RealSOTATrainer:
    """真实SOTA模型训练器"""
    
    def __init__(self, device='cpu'):
        self.device = device
        self.scaler = StandardScaler()
        
    def prepare_data(self, data: pd.DataFrame, seq_len: int = 60) -> Tuple[torch.Tensor, torch.Tensor, np.ndarray]:
        """准备训练数据"""
        # 标准化
        values = data['y'].values.reshape(-1, 1)
        scaled_values = self.scaler.fit_transform(values).flatten()
        
        # 创建序列
        X, y = [], []
        for i in range(len(scaled_values) - seq_len):
            X.append(scaled_values[i:(i + seq_len)])
            y.append(scaled_values[i + seq_len])
        
        X = torch.FloatTensor(X).unsqueeze(-1)  # (samples, seq_len, features)
        y = torch.FloatTensor(y)
        
        return X, y, scaled_values
    
    def train_model(self, model: nn.Module, X: torch.Tensor, y: torch.Tensor, 
                   epochs: int = 100, lr: float = 0.001) -> Dict[str, Any]:
        """训练模型"""
        start_time = datetime.now()
        model.to(self.device)
        
        # 数据分割
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # 优化器和损失函数
        optimizer = optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()
        
        # 训练历史
        train_losses = []
        val_losses = []
        best_val_loss = float('inf')
        patience = 10
        patience_counter = 0
        
        for epoch in range(epochs):
            # 训练
            model.train()
            optimizer.zero_grad()
            
            train_pred = model(X_train.to(self.device))
            train_loss = criterion(train_pred.squeeze(), y_train.to(self.device))
            train_loss.backward()
            optimizer.step()
            
            # 验证
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val.to(self.device))
                val_loss = criterion(val_pred.squeeze(), y_val.to(self.device))
            
            train_losses.append(train_loss.item())
            val_losses.append(val_loss.item())
            
            # 早停检查
            if val_loss < best_val_loss:
                best_val_loss = val_loss.item()
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"早停在epoch {epoch}")
                    break
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'training_time': training_time,
            'final_train_loss': train_losses[-1],
            'final_val_loss': val_losses[-1],
            'convergence_epochs': len(train_losses),
            'train_history': train_losses,
            'val_history': val_losses
        }
    
    def evaluate_model(self, model: nn.Module, X_test: torch.Tensor, y_test: torch.Tensor) -> RealModelPerformance:
        """评估模型性能"""
        start_time = datetime.now()
        
        model.eval()
        with torch.no_grad():
            predictions = model(X_test.to(self.device)).cpu().numpy().flatten()
        
        inference_time = (datetime.now() - start_time).total_seconds()
        
        # 反标准化
        y_true = self.scaler.inverse_transform(y_test.numpy().reshape(-1, 1)).flatten()
        y_pred = self.scaler.inverse_transform(predictions.reshape(-1, 1)).flatten()
        
        # 计算指标
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        r2 = r2_score(y_true, y_pred)
        
        # 模型大小
        model_size = sum(p.numel() for p in model.parameters())
        
        return RealModelPerformance(
            model_name=model.__class__.__name__,
            mae=mae,
            rmse=rmse,
            mape=mape,
            r2=r2,
            training_time=0,  # 会在外部设置
            inference_time=inference_time,
            model_size=model_size,
            convergence_epochs=0  # 会在外部设置
        )
    
    def predict_future(self, model: nn.Module, last_sequence: np.ndarray, periods: int) -> np.ndarray:
        """预测未来值"""
        model.eval()
        predictions = []
        
        # 标准化最后的序列
        current_seq = self.scaler.transform(last_sequence.reshape(-1, 1)).flatten()
        current_seq = torch.FloatTensor(current_seq).unsqueeze(0).unsqueeze(-1)
        
        with torch.no_grad():
            for _ in range(periods):
                # 预测下一个值
                pred = model(current_seq.to(self.device)).cpu().item()
                predictions.append(pred)
                
                # 更新序列
                current_seq = torch.cat([current_seq[:, 1:, :], 
                                       torch.FloatTensor([[[pred]]])], dim=1)
        
        # 反标准化预测结果
        predictions = np.array(predictions).reshape(-1, 1)
        predictions = self.scaler.inverse_transform(predictions).flatten()
        
        return predictions

def run_real_sota_comparison(data: pd.DataFrame, test_ratio: float = 0.2, seq_len: int = 60) -> Dict[str, Any]:
    """运行真实SOTA模型比较"""
    logger.info("开始真实SOTA模型比较...")
    
    trainer = RealSOTATrainer()
    
    # 准备数据
    X, y, scaled_values = trainer.prepare_data(data, seq_len)
    split_idx = int(len(X) * (1 - test_ratio))
    
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    # 初始化模型
    models = {
        'TimeMixer': RealTimeMixerModel(seq_len=seq_len),
        'ModernTCN': RealModernTCNModel(),
        'MICN': RealMICNModel(seq_len=seq_len)
    }
    
    results = {}
    
    for model_name, model in models.items():
        try:
            logger.info(f"训练 {model_name}...")
            
            # 训练模型
            train_result = trainer.train_model(model, X_train, y_train)
            
            # 评估模型
            performance = trainer.evaluate_model(model, X_test, y_test)
            performance.training_time = train_result['training_time']
            performance.convergence_epochs = train_result['convergence_epochs']
            
            # 预测未来
            last_seq = data['y'].tail(seq_len).values
            future_pred = trainer.predict_future(model, last_seq, 30)
            
            results[model_name] = {
                'performance': performance,
                'train_result': train_result,
                'future_predictions': future_pred,
                'model': model
            }
            
            logger.info(f"{model_name} - MAE: {performance.mae:.2f}, R²: {performance.r2:.4f}, 训练时间: {performance.training_time:.1f}s")
            
        except Exception as e:
            logger.error(f"{model_name} 训练失败: {e}")
            results[model_name] = {'error': str(e)}
    
    return results

# Prophet基准比较
def add_prophet_baseline(data: pd.DataFrame, periods: int = 30) -> Dict[str, Any]:
    """添加Prophet基准比较"""
    from prophet import Prophet
    
    start_time = datetime.now()
    
    # 训练Prophet
    prophet_data = data[['ds', 'y']].copy()
    prophet_data['ds'] = pd.to_datetime(prophet_data['ds'])
    
    model = Prophet(
        weekly_seasonality=True,
        yearly_seasonality=True,
        daily_seasonality=False
    )
    
    # 分割数据
    split_idx = int(len(prophet_data) * 0.8)
    train_data = prophet_data[:split_idx]
    test_data = prophet_data[split_idx:]
    
    model.fit(train_data)
    
    # 评估
    test_future = model.make_future_dataframe(periods=len(test_data), freq='D', include_history=False)
    test_forecast = model.predict(test_future)
    
    y_true = test_data['y'].values
    y_pred = test_forecast['yhat'].values
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    r2 = r2_score(y_true, y_pred)
    
    training_time = (datetime.now() - start_time).total_seconds()
    
    # 未来预测
    future = model.make_future_dataframe(periods=periods, freq='D')
    forecast = model.predict(future)
    future_pred = forecast.tail(periods)['yhat'].values
    
    performance = RealModelPerformance(
        model_name="Prophet",
        mae=mae,
        rmse=rmse,
        mape=mape,
        r2=r2,
        training_time=training_time,
        inference_time=0.1,
        model_size=0,
        convergence_epochs=1
    )
    
    return {
        'performance': performance,
        'future_predictions': future_pred,
        'forecast_df': forecast.tail(periods)
    }

def add_neuralprophet_baseline(data: pd.DataFrame, periods: int = 30) -> Dict[str, Any]:
    """添加真正的NeuralProphet基准比较"""
    try:
        from neuralprophet import NeuralProphet
        import warnings
        warnings.filterwarnings('ignore')
        
        start_time = datetime.now()
        
        # 准备NeuralProphet数据
        np_data = data[['ds', 'y']].copy()
        np_data['ds'] = pd.to_datetime(np_data['ds'])
        
        # 创建NeuralProphet模型
        model = NeuralProphet(
            n_forecasts=1,
            n_lags=7,  # 使用过去7天的数据
            weekly_seasonality=True,
            yearly_seasonality=True,
            daily_seasonality=False,
            epochs=50,  # 减少epochs以加快训练
            learning_rate=0.01,
            batch_size=32
        )
        
        # 分割数据
        split_idx = int(len(np_data) * 0.8)
        train_data = np_data[:split_idx].copy()
        test_data = np_data[split_idx:].copy()
        
        # 训练模型
        model.fit(train_data, freq='D')
        
        # 创建测试未来数据框
        test_future = model.make_future_dataframe(train_data, periods=len(test_data))
        
        # 预测
        test_forecast = model.predict(test_future)
        
        # 获取测试期间的预测
        test_predictions = test_forecast.tail(len(test_data))
        
        y_true = test_data['y'].values
        y_pred = test_predictions['yhat1'].values
        
        # 计算指标
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        r2 = r2_score(y_true, y_pred)
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # 未来预测
        future_df = model.make_future_dataframe(np_data, periods=periods)
        forecast = model.predict(future_df)
        future_pred = forecast.tail(periods)['yhat1'].values
        
        performance = RealModelPerformance(
            model_name="NeuralProphet",
            mae=mae,
            rmse=rmse,
            mape=mape,
            r2=r2,
            training_time=training_time,
            inference_time=0.2,
            model_size=0,  # NeuralProphet模型大小较难计算
            convergence_epochs=50
        )
        
        return {
            'performance': performance,
            'future_predictions': future_pred,
            'forecast_df': forecast.tail(periods)
        }
        
    except Exception as e:
        logger.error(f"NeuralProphet训练失败: {e}")
        return {'error': str(e)}