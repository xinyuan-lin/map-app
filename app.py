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

# Ignore warnings
warnings.filterwarnings('ignore')

app = Flask(__name__, static_folder='static')

# Global variables to store loaded data
mvbs_dataset = None
data_cache = {}
# Ensure the static directory exists
OUTPUT_DIR = "static/echograms"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_dataset():
    """Load MVBS dataset and perform necessary preprocessing"""
    global mvbs_dataset
    if mvbs_dataset is None:
        try:
            print("Loading MVBS dataset...")
            mvbs_dataset = xr.open_dataset("concatenated_MVBS.nc")
            print("Dataset loaded successfully")
        except Exception as e:
            print(f"Error loading dataset: {e}")
            mvbs_dataset = None  # Prevent using None in case of error
    return mvbs_dataset

@app.route('/')
def index():
    """Provide the main page"""
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
        # Get request parameters
        point_index = int(request.args.get('pointIndex', 0))
        channel_index = int(request.args.get('channelIndex', 0))
        vmin = float(request.args.get('vmin', -80))
        vmax = float(request.args.get('vmax', -30))

        ds = load_dataset()
        if ds is None:
            return jsonify({"error": "Unable to load dataset"}), 500

        # Get channel name and time
        channels = ds.channel.values
        if channel_index >= len(channels):
            return jsonify({"error": "Invalid channel index"}), 400
        channel_name = channels[channel_index]

        time_points = ds.ping_time.values
        if point_index >= len(time_points):
            return jsonify({"error": "Invalid time index"}), 400
        time_point = time_points[point_index]

        # Generate echogram with specified parameters
        echogram = ds.eshader.echogram(
            channel=[channel_name],
            cmap=[
                "#FFFFFF", "#9F9F9F", "#5F5F5F",
                "#0000FF", "#00007F", "#00BF00",
                "#007F00", "#FFFF00", "#FF7F00",
                "#FF00BF", "#FF0000", "#A6533C", "#783C28"
            ],
            vmin=vmin,
            vmax=vmax,
        )

        # Add title with point and channel information
        time_str = str(time_point).split('.')[0]  # Remove microseconds
        title = f"Echogram at {time_str} - Channel: {channel_name}"
        
        # Create a Panel layout with title
        layout = pn.Column(
            pn.pane.Markdown(f"# {title}"),
            pn.pane.Markdown(f"Sv range: {vmin} to {vmax} dB"),
            echogram
        )

        # Save echogram as an HTML file
        output_path = os.path.join(OUTPUT_DIR, f"echogram_{point_index}_{channel_index}_{vmin}_{vmax}.html")
        layout.save(output_path)  # Saves echogram as an interactive HTML file

        return send_file(output_path, mimetype='text/html')

    except Exception as e:
        app.logger.error(f"Error displaying echogram: {str(e)}")
        traceback.print_exc()  # Print full error traceback
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)