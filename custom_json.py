"""
自定义JSON编码器和工具函数，用于处理NumPy数组和特殊值
"""

import json
import numpy as np
import math
from datetime import datetime

class NumpyJSONEncoder(json.JSONEncoder):
    """处理NumPy数组和特殊浮点值的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            # 递归处理数组中的每个元素
            return self.process_numpy_array(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, np.datetime64):
            return str(obj)
        return super().default(obj)
    
    def process_numpy_array(self, arr):
        """递归处理NumPy数组，确保所有NaN和Inf值都被转换为None"""
        # 处理多维数组
        if arr.ndim > 1:
            return [self.process_numpy_array(row) for row in arr]
        # 处理一维数组
        return [None if (np.isnan(x) or np.isinf(x)) else 
                int(x) if isinstance(x, (np.integer, np.int64, np.int32)) else
                float(x) if isinstance(x, (np.floating, np.float64, np.float32)) else
                str(x) if isinstance(x, (np.datetime64, datetime)) else x
                for x in arr]

def safe_json_dumps(obj):
    """安全地将对象转换为JSON字符串，处理所有特殊值"""
    return json.dumps(obj, cls=NumpyJSONEncoder)

def preprocess_data(data):
    """预处理数据，确保所有无效值都被替换为None"""
    if isinstance(data, dict):
        return {k: preprocess_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [preprocess_data(item) for item in data]
    elif isinstance(data, np.ndarray):
        # 递归处理数组
        encoder = NumpyJSONEncoder()
        return encoder.process_numpy_array(data)
    elif isinstance(data, (np.integer, np.int64, np.int32)):
        return int(data)
    elif isinstance(data, (np.floating, np.float64, np.float32)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, (datetime, np.datetime64)):
        return str(data)
    return data