#!/usr/bin/env python
"""
回波图批处理工具 - 用于批量生成回波图图像
"""

import os
import argparse
import matplotlib.pyplot as plt
from data_processor import MVBSProcessor
from multiprocessing import Pool, cpu_count
import numpy as np
import tqdm
import json

def process_point(args):
    """处理单个点位的回波图，用于并行处理"""
    point_index, channel_index, config = args
    
    processor = MVBSProcessor(config['data_file'])
    output_path = os.path.join(
        config['output_dir'], 
        f"echogram_point{point_index:04d}_channel{channel_index}.png"
    )
    
    try:
        processor.plot_echogram(
            point_index=point_index,
            channel_index=channel_index,
            vmin=config['vmin'],
            vmax=config['vmax'],
            save_path=output_path
        )
        processor.close()
        return True
    except Exception as e:
        print(f"处理点 {point_index} 通道 {channel_index} 时出错: {e}")
        processor.close()
        return False

def generate_echograms(data_file, output_dir, channels=None, points=None, 
                      step=1, vmin=-80, vmax=-30, workers=None):
    """
    生成一系列回波图
    
    参数:
        data_file (str): NetCDF数据文件路径
        output_dir (str): 输出目录
        channels (list, optional): 要处理的通道索引列表，默认为所有通道
        points (list, optional): 要处理的点位索引列表，默认为所有点位
        step (int): 点位索引的步进值，默认为1（处理所有点）
        vmin (float): 颜色范围最小值
        vmax (float): 颜色范围最大值
        workers (int, optional): 并行工作进程数，默认为CPU核心数
    
    返回:
        int: 成功生成的回波图数量
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载数据集获取维度信息
    processor = MVBSProcessor(data_file)
    total_channels = len(processor.dataset.channel)
    total_points = len(processor.dataset.ping_time)
    
    # 保存数据集概览
    summary = processor.get_summary()
    with open(os.path.join(output_dir, 'dataset_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    # 确定要处理的通道
    if channels is None:
        channels = list(range(total_channels))
    else:
        channels = [c for c in channels if 0 <= c < total_channels]
    
    # 确定要处理的点位
    if points is None:
        points = list(range(0, total_points, step))
    else:
        points = [p for p in points if 0 <= p < total_points]
    
    processor.close()
    
    print(f"将处理 {len(channels)} 个通道的 {len(points)} 个点位的回波图")
    
    # 准备任务列表
    tasks = []
    for point_index in points:
        for channel_index in channels:
            tasks.append((
                point_index, 
                channel_index, 
                {
                    'data_file': data_file,
                    'output_dir': output_dir,
                    'vmin': vmin,
                    'vmax': vmax
                }
            ))
    
    # 确定工作进程数
    if workers is None:
        workers = max(1, cpu_count() - 1)
    
    # 使用进程池并行处理
    successful = 0
    with Pool(processes=workers) as pool:
        results = list(tqdm.tqdm(
            pool.imap(process_point, tasks),
            total=len(tasks),
            desc="生成回波图"
        ))
        successful = sum(results)
    
    print(f"完成! 成功生成 {successful}/{len(tasks)} 张回波图")
    return successful

def generate_video_frames(data_file, output_dir, channel_index=0, 
                         vmin=-80, vmax=-30, format='png'):
    """
    为单个通道的所有点位生成回波图，用于创建视频
    
    参数:
        data_file (str): NetCDF数据文件路径
        output_dir (str): 输出目录
        channel_index (int): 要处理的通道索引
        vmin (float): 颜色范围最小值
        vmax (float): 颜色范围最大值
        format (str): 输出图像格式，默认为png
    
    返回:
        int: 成功生成的帧数
    """
    # 创建输出目录
    frames_dir = os.path.join(output_dir, f'channel{channel_index}_frames')
    os.makedirs(frames_dir, exist_ok=True)
    
    # 加载数据集
    processor = MVBSProcessor(data_file)
    total_points = len(processor.dataset.ping_time)
    channel_name = processor.dataset.channel.values[channel_index]
    
    print(f"为通道 {channel_name} 生成 {total_points} 帧")
    
    # 生成固定通道的所有点位回波图
    successful = 0
    for point_index in tqdm.tqdm(range(total_points), desc="生成视频帧"):
        try:
            output_path = os.path.join(frames_dir, f"frame_{point_index:04d}.{format}")
            processor.plot_echogram(
                point_index=point_index,
                channel_index=channel_index,
                vmin=vmin,
                vmax=vmax,
                save_path=output_path
            )
            successful += 1
        except Exception as e:
            print(f"处理帧 {point_index} 时出错: {e}")
    
    processor.close()
    print(f"完成! 成功生成 {successful}/{total_points} 帧")
    
    # 生成视频创建命令提示
    print("\n要创建视频，您可以使用以下FFmpeg命令:")
    print(f"ffmpeg -framerate 10 -i {frames_dir}/frame_%04d.{format} -c:v libx264 -pix_fmt yuv420p -crf 23 {output_dir}/channel{channel_index}_echogram.mp4")
    
    return successful

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="回波图批处理工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 批量生成回波图的命令
    batch_parser = subparsers.add_parser("batch", help="批量生成回波图")
    batch_parser.add_argument("data_file", help="NetCDF数据文件路径")
    batch_parser.add_argument("output_dir", help="输出目录")
    batch_parser.add_argument("--channels", type=int, nargs="+", help="要处理的通道索引列表")
    batch_parser.add_argument("--points", type=int, nargs="+", help="要处理的点位索引列表")
    batch_parser.add_argument("--step", type=int, default=10, help="点位索引的步进值，默认为10")
    batch_parser.add_argument("--vmin", type=float, default=-80, help="颜色范围最小值")
    batch_parser.add_argument("--vmax", type=float, default=-30, help="颜色范围最大值")
    batch_parser.add_argument("--workers", type=int, help="并行工作进程数")
    
    # 生成视频帧的命令
    video_parser = subparsers.add_parser("video", help="生成回波图视频帧")
    video_parser.add_argument("data_file", help="NetCDF数据文件路径")
    video_parser.add_argument("output_dir", help="输出目录")
    video_parser.add_argument("--channel", type=int, default=0, help="要处理的通道索引")
    video_parser.add_argument("--vmin", type=float, default=-80, help="颜色范围最小值")
    video_parser.add_argument("--vmax", type=float, default=-30, help="颜色范围最大值")
    video_parser.add_argument("--format", choices=["png", "jpg"], default="png", help="输出图像格式")
    
    args = parser.parse_args()
    
    if args.command == "batch":
        generate_echograms(
            data_file=args.data_file,
            output_dir=args.output_dir,
            channels=args.channels,
            points=args.points,
            step=args.step,
            vmin=args.vmin,
            vmax=args.vmax,
            workers=args.workers
        )
    elif args.command == "video":
        generate_video_frames(
            data_file=args.data_file,
            output_dir=args.output_dir,
            channel_index=args.channel,
            vmin=args.vmin,
            vmax=args.vmax,
            format=args.format
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()