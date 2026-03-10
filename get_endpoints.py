from typing import List, Tuple
from detect_wire_endpoints import detect_wire_endpoints as detect_color_endpoints

def get_endpoints(image_path: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """返回所有颜色导线的端点，扁平长列表 [(p1,p2), ...]"""
    all_pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    # 这里可以添加更多颜色的检测，例如黄色、蓝色等
    yellow_endpoints = detect_color_endpoints(image_path,((20, 100, 100), (30, 255, 255)),'yellow')
    red_endpoints = detect_color_endpoints(image_path,((15, 70, 50), (40, 255, 255)),'red')

    all_pairs.extend(yellow_endpoints)
    all_pairs.extend(red_endpoints)

    return all_pairs

