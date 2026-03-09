from typing import List, Tuple, Dict, Set, Any
from collections import defaultdict

# 导入您自定义的函数
from get_endpoints import get_endpoints
from inferrence import get_element_location


def is_point_in_bbox(point: Tuple[int, int], bbox: Tuple[int, int, int, int], tol: int = 20) -> bool:
    """判断点是否在边界框内"""
    x, y = point
    x1, y1, x2, y2 = bbox
    scaled_x, scaled_y = 2 * x, 2 * y
    return (x1 - tol <= scaled_x <= x2 + tol and
            y1 - tol <= scaled_y <= y2 + tol)


def get_circuit_connections(image_path: str) -> Dict[str, Any]:
    """
    获取电路连接关系（支持多个相同元件）

    返回格式:
    {
        "elements": ["V_s", "R_x", "R_box_1", "R_box_2", "S_G", "S_rev", "G"],
        "connections": {
            "V_s": ["S_rev"],
            "S_rev": ["V_s", "R_box_1", "R_box_2", "R_x"],
            "G": ["S_G"],
            "S_G": ["G", "R_box_1", "R_box_2"],
            "R_box_1": ["S_rev", "S_G"],
            "R_box_2": ["S_rev", "S_G"],
            "R_x": ["S_rev"]
        },
        "wires": [
            ["V_s", "S_rev"],
            ["G", "S_G"],
            ["S_G", "R_box_1"],
            ["S_G", "R_box_2"],
            ["R_box_1", "S_rev"],
            ["R_box_2", "S_rev"],
            ["R_x", "S_rev"]
        ]
    }
    """
    # 获取元件位置和类型
    elements = get_element_location(image_path)
    # 获取导线端点
    endpoints = get_endpoints(image_path)

    # 处理元件标识符（支持多个相同元件）
    element_ids = []
    element_bboxes = {}
    element_counters = defaultdict(int)

    for bbox, elem_type in elements:
        element_counters[elem_type] += 1
        if element_counters[elem_type] > 1:
            elem_id = f"{elem_type}_{element_counters[elem_type]}"
        else:
            elem_id = elem_type

        element_ids.append(elem_id)
        element_bboxes[elem_id] = bbox

    # 构建连接关系
    connections = {elem_id: [] for elem_id in element_ids}
    wires = []

    for start_point, end_point in endpoints:
        connected_elements = []

        # 检查导线两端连接的元件
        for elem_id, bbox in element_bboxes.items():
            if is_point_in_bbox(start_point, bbox) or is_point_in_bbox(end_point, bbox):
                connected_elements.append(elem_id)

        # 记录导线连接
        if len(connected_elements) >= 2:
            wires.append(connected_elements)

            # 更新连接关系
            for i in range(len(connected_elements)):
                for j in range(i + 1, len(connected_elements)):
                    elem1, elem2 = connected_elements[i], connected_elements[j]
                    if elem2 not in connections[elem1]:
                        connections[elem1].append(elem2)
                    if elem1 not in connections[elem2]:
                        connections[elem2].append(elem1)

    return {
        "elements": element_ids,
        "connections": connections,
        "wires": wires
    }


def print_connections_summary(connection_data: Dict[str, Any]):
    """打印连接关系摘要"""
    print("电路连接关系摘要:")
    print("=" * 50)

    print("\n检测到的元件:")
    for elem in connection_data["elements"]:
        print(f"  {elem}")

    print("\n连接关系:")
    for elem, connected in sorted(connection_data["connections"].items()):
        if connected:
            print(f"  {elem} → {', '.join(sorted(connected))}")

    print("\n导线连接:")
    for i, wire in enumerate(connection_data["wires"], 1):
        print(f"  导线{i}: {' ↔ '.join(wire)}")

'''
# 使用示例
if __name__ == "__main__":
    image_path = "D:\\test\\6.jpg"

    # 获取连接关系
    connection_data = get_circuit_connections(image_path)

    # 打印摘要
    print_connections_summary(connection_data)

    # 返回的数据可以直接使用
    print("\n返回的数据结构:")
    print(f"元件列表: {sorted(connection_data['elements'])}")
    print(f"连接关系字典键: {sorted(connection_data['connections'].keys())}")
    print(f"导线数量: {len(connection_data['wires'])}")'''