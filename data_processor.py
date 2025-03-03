import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import os

class MVBSProcessor:
    """处理MVBS (Mean Volume Backscattering Strength) 数据的工具类"""
    
    def __init__(self, file_path):
        """
        初始化处理器
        
        参数:
            file_path (str): MVBS NetCDF文件路径
        """
        self.file_path = file_path
        self.dataset = None
        self.load_dataset()
    
    def load_dataset(self):
        """加载MVBS数据集"""
        self.dataset = xr.open_dataset(self.file_path)
        print(f"加载了数据集 {self.file_path}")
        print(f"数据集维度: {dict(self.dataset.dims)}")
        return self.dataset
    
    def get_summary(self):
        """获取数据集基本信息摘要"""
        if self.dataset is None:
            return "数据集未加载"
        
        summary = {
            "时间范围": [
                str(self.dataset.ping_time.values[0]),
                str(self.dataset.ping_time.values[-1])
            ],
            "经度范围": [
                float(self.dataset.longitude.min().values),
                float(self.dataset.longitude.max().values)
            ],
            "纬度范围": [
                float(self.dataset.latitude.min().values),
                float(self.dataset.latitude.max().values)
            ],
            "深度范围": [
                float(self.dataset.echo_range.min().values),
                float(self.dataset.echo_range.max().values)
            ],
            "Sv范围": [
                float(self.dataset.Sv.min().values),
                float(self.dataset.Sv.max().values)
            ],
            "频率通道": list(self.dataset.channel.values),
            "点位数量": len(self.dataset.ping_time),
            "深度采样数": len(self.dataset.echo_range)
        }
        
        return summary
    
    def extract_trajectory(self):
        """提取船只轨迹信息"""
        if self.dataset is None:
            return None
        
        trajectory = {
            "latitude": self.dataset.latitude.values.tolist(),
            "longitude": self.dataset.longitude.values.tolist(),
            "time": [str(t) for t in self.dataset.ping_time.values],
        }
        
        return trajectory
    
    def get_echogram_data(self, point_index, channel_index):
        """
        获取特定点位和通道的回波图数据
        
        参数:
            point_index (int): 点位索引
            channel_index (int): 通道索引
            
        返回:
            dict: 回波图数据
        """
        if self.dataset is None:
            return None
        
        channel_name = self.dataset.channel.values[channel_index]
        time_point = self.dataset.ping_time.values[point_index]
        
        # 提取Sv数据
        sv_data = self.dataset.Sv.sel(
            channel=channel_name, 
            ping_time=time_point
        ).values
        
        # 准备返回数据
        echogram_data = {
            "svValues": [sv_data.tolist()],  # 包装为2D数组
            "depths": self.dataset.echo_range.values.tolist(),
            "title": f"{channel_name} 回波图",
            "time": str(time_point)
        }
        
        return echogram_data
    
    def plot_echogram(self, point_index, channel_index, vmin=-80, vmax=-30, save_path=None):
        """
        绘制回波图并可选择性保存
        
        参数:
            point_index (int): 点位索引
            channel_index (int): 通道索引
            vmin (float): 颜色刻度最小值 (dB)
            vmax (float): 颜色刻度最大值 (dB)
            save_path (str, optional): 保存路径，若不提供则显示图像
            
        返回:
            matplotlib.figure.Figure: 生成的图像对象
        """
        if self.dataset is None:
            return None
        
        channel_name = self.dataset.channel.values[channel_index]
        time_point = self.dataset.ping_time.values[point_index]
        
        # 提取Sv数据
        sv_data = self.dataset.Sv.sel(
            channel=channel_name, 
            ping_time=time_point
        ).values
        
        # 准备深度
        depths = self.dataset.echo_range.values
        
        # 创建图像
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 绘制热图
        im = ax.imshow(sv_data.reshape(1, -1), aspect='auto', cmap='jet', 
                       extent=[0, 1, depths[-1], depths[0]], vmin=vmin, vmax=vmax)
        
        # 设置标题和标签
        ax.set_title(f"{channel_name} Echogram at {time_point}")
        ax.set_ylabel('Depth (m)')
        ax.set_xlabel('Position')
        
        # 添加颜色条
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('Sv (dB re 1 m⁻¹)')
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.tight_layout()
            plt.show()
        
        return fig
    
    def export_transect(self, channel_index, depth_range=None, output_file=None):
        """
        导出特定通道的断面数据
        
        参数:
            channel_index (int): 通道索引
            depth_range (tuple, optional): 深度范围 (min, max)
            output_file (str, optional): 输出文件路径
            
        返回:
            pandas.DataFrame: 断面数据
        """
        if self.dataset is None:
            return None
        
        channel_name = self.dataset.channel.values[channel_index]
        
        # 选择通道数据
        channel_data = self.dataset.Sv.sel(channel=channel_name)
        
        # 如果指定了深度范围，则筛选
        if depth_range:
            min_depth, max_depth = depth_range
            depth_mask = (self.dataset.echo_range >= min_depth) & (self.dataset.echo_range <= max_depth)
            channel_data = channel_data.sel(echo_range=self.dataset.echo_range[depth_mask])
        
        # 创建DataFrame
        df = channel_data.to_dataframe().reset_index()
        
        # 如果指定了输出文件，则保存
        if output_file:
            df.to_csv(output_file, index=False)
        
        return df
    
    def close(self):
        """关闭数据集，释放资源"""
        if self.dataset is not None:
            self.dataset.close()
            self.dataset = None
            print("数据集已关闭")

# 示例用法
if __name__ == "__main__":
    # 创建处理器
    processor = MVBSProcessor("concatenated_MVBS.nc")
    
    # 获取数据摘要
    summary = processor.get_summary()
    print("数据摘要:", summary)
    
    # 提取轨迹
    trajectory = processor.extract_trajectory()
    print(f"轨迹点数量: {len(trajectory['latitude'])}")
    
    # 绘制示例回波图
    processor.plot_echogram(
        point_index=0,  # 第一个点位
        channel_index=0,  # 第一个通道 (18 kHz)
        save_path="sample_echogram.png"
    )
    
    # 导出断面数据
    transect_df = processor.export_transect(
        channel_index=0,
        depth_range=(0, 500),
        output_file="transect_data.csv"
    )
    
    # 关闭处理器
    processor.close()