from flask import Flask, jsonify, request, send_from_directory, make_response, send_file
import xarray as xr
import numpy as np
import os
import json
import echoshader  # Import echoshader
import panel as pn  # Panel is used to display echogram
from datetime import datetime
import warnings
from custom_json import NumpyJSONEncoder, preprocess_data, safe_json_dumps
import traceback  # To print detailed error logs

# 忽略警告
warnings.filterwarnings('ignore')

app = Flask(__name__, static_folder='static')

# 全局变量，存储已加载的数据
mvbs_dataset = None
data_cache = {}
# Ensure the static directory exists
OUTPUT_DIR = "static/echograms"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_dataset():
    """加载MVBS数据集并进行必要的预处理"""
    global mvbs_dataset
    if mvbs_dataset is None:
        try:
            print("加载MVBS数据集...")
            mvbs_dataset = xr.open_dataset("concatenated_MVBS.nc")
            print("数据集加载完成")
        except Exception as e:
            print(f"加载数据集时出错: {e}")
            mvbs_dataset = None  # 防止意外情况下仍使用 None
    return mvbs_dataset

@app.route('/')
def index():
    """提供主页面"""
    return send_from_directory('.', 'index.html')

@app.route('/api/acoustic-data')
def get_acoustic_data():
    """Provide acoustic data (trajectory points, channels, etc.)"""
    try:
        ds = load_dataset()
        if ds is None:
            app.logger.error("Failed to load dataset.")
            return jsonify({"error": "Failed to load dataset"}), 500

        # Debugging: Print dataset info
        print("Dataset loaded successfully.")
        print("Dataset variables:", ds.variables.keys())

        # Check for missing latitude/longitude
        if 'latitude' not in ds or 'longitude' not in ds:
            app.logger.error("Dataset does not contain latitude/longitude.")
            return jsonify({"error": "Missing latitude/longitude in dataset"}), 500

        # Function to replace NaN values safely
        def replace_nan(arr):
            return [None if isinstance(val, float) and np.isnan(val) else val for val in arr]

        # Convert dataset to JSON-compatible format
        data = {
            'latitude': replace_nan(ds.latitude.values.tolist()),
            'longitude': replace_nan(ds.longitude.values.tolist()),
            'time': [str(t) for t in ds.ping_time.values],
            'channels': [str(c) for c in ds.channel.values],
            'echo_range': ds.echo_range.values.tolist()
        }

        # Debugging: Print small sample of data
        print("Processed Data Sample:", {key: data[key][:5] for key in data if isinstance(data[key], list)})

        response = make_response(safe_json_dumps(data))
        response.headers['Content-Type'] = 'application/json'
        return response

    except Exception as e:
        error_msg = f"Error fetching acoustic data: {str(e)}"
        app.logger.error(error_msg)
        traceback.print_exc()  # Print full error traceback
        return jsonify({'error': error_msg}), 500


@app.route('/api/echogram')
def get_echogram():
    """Generates an echogram and returns it as an HTML file."""
    try:
        point_index = int(request.args.get('pointIndex', 0))
        channel_index = int(request.args.get('channelIndex', 0))

        ds = load_dataset()
        if ds is None:
            return jsonify({"error": "无法加载数据集"}), 500

        # 获取通道名称和时间
        channels = ds.channel.values
        if channel_index >= len(channels):
            return jsonify({"error": "无效的通道索引"}), 400
        channel_name = channels[channel_index]

        time_points = ds.ping_time.values
        if point_index >= len(time_points):
            return jsonify({"error": "无效的时间索引"}), 400
        time_point = time_points[point_index]

        # 生成 echogram
        echogram = ds.eshader.echogram(
            channel=[channel_name],
            cmap=[
                "#FFFFFF", "#9F9F9F", "#5F5F5F",
                "#0000FF", "#00007F", "#00BF00",
                "#007F00", "#FFFF00", "#FF7F00",
                "#FF00BF", "#FF0000", "#A6533C", "#783C28"
            ],
            vmin=-80,
            vmax=-30,
        )

        # Save echogram as an HTML file
        output_path = os.path.join(OUTPUT_DIR, f"echogram_{point_index}_{channel_index}.html")
        pn.panel(echogram).save(output_path)  # Saves echogram as an interactive HTML file

        return send_file(output_path, mimetype='text/html')

    except Exception as e:
        app.logger.error(f"生成 echogram 时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
