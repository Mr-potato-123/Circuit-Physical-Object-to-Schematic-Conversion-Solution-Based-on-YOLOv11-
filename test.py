
import cv2
import numpy as np
from typing import List, Tuple
import math


# ----------------------------------------------------------
# 主函数：颜色区间 → 端点对（每一步都弹窗显示）
# ----------------------------------------------------------
def detect_wire_endpoints(
        image_path: str,
        color_range: Tuple[Tuple[int, int, int], Tuple[int, int, int]],
        mode: str
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise FileNotFoundError(image_path)
    img_bgr = cv2.resize(img_bgr, (640, 640), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 1. 颜色二值化
    if mode == 'red':
        low1 = np.array([0, 70, 50]);  high1 = np.array([15, 255, 255])
        low2 = np.array([165, 50, 50]); high2 = np.array([180, 255, 255])
        mask = cv2.bitwise_or(cv2.inRange(hsv, low1, high1),
                              cv2.inRange(hsv, low2, high2))
    else:
        low, high = map(np.array, color_range)
        mask = cv2.inRange(hsv, low, high)
    cv2.imshow("1.color_mask", mask)
    cv2.waitKey(0)

    # 2. 加粗
    thickened = _thicken_wires(mask)
    cv2.imshow("2.thickened", thickened)
    cv2.waitKey(0)

    # 3. 骨架化（未缝合）
    skel_raw = _thinning_zs(thickened)
    cv2.imshow("3a.skel_before_bridge", skel_raw)
    cv2.waitKey(0)

    # 4. 断点缝合
    skel = _bridge_gaps(thickened)          # 注意：内部会再骨架化一次
    cv2.imshow("4.skel_bridged", skel)
    cv2.waitKey(0)

    # 5. 端点检测（仅画端点，未配对）
    end_pts = _endpoints(skel)
    end_vis = cv2.cvtColor(skel, cv2.COLOR_GRAY2BGR)
    for (x, y) in end_pts:
        cv2.circle(end_vis, (x, y), 4, (0, 0, 255), -1)
    cv2.imshow("4a.endpoints_before_pairing", end_vis)
    cv2.waitKey(0)

    # 6. 端点配对（未合并）
    pairs_raw = _pair_endpoints(skel)
    pair_vis = img_bgr.copy()
    for (x1, y1), (x2, y2) in pairs_raw:
        cv2.circle(pair_vis, (x1, y1), 5, (0, 0, 255), -1)
        cv2.circle(pair_vis, (x2, y2), 5, (0, 0, 255), -1)
        cv2.line(pair_vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.imshow("5a.paired_before_merge", pair_vis)
    cv2.waitKey(0)

    # 7. 端点合并（最终）
    pairs = merge_wires_with_threshold(pairs_raw, max_dist=20)
    final_vis = img_bgr.copy()
    for (x1, y1), (x2, y2) in pairs:
        cv2.circle(final_vis, (x1, y1), 5, (0, 0, 255), -1)
        cv2.circle(final_vis, (x2, y2), 5, (0, 0, 255), -1)
        cv2.line(final_vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        dist = math.dist((x1, y1), (x2, y2))
        mid = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.putText(final_vis, f"{dist:.1f}", mid,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.imshow("6.final_result", final_vis)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return pairs

# ------------------------------------------------------------
# 2. 加粗函数
# ------------------------------------------------------------
def _thicken_wires(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), np.uint8)
    thickened = cv2.dilate(mask, kernel, iterations=1)
    return thickened


# ------------------------------------------------------------
# 3. Zhang-Suen 骨架化
# ------------------------------------------------------------
def _thinning_zs(bw: np.ndarray) -> np.ndarray:
    img = (bw > 0).astype(np.uint8)
    h, w = img.shape
    dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1),
            (1, 0), (1, -1), (0, -1), (-1, -1)]

    def n(x, y):
        return [img[x + dx, y + dy] if 0 <= x + dx < h and 0 <= y + dy < w else 0
                for dx, dy in dirs]

    def iterate(step):
        mark = np.zeros_like(img)
        for i in range(1, h - 1):
            for j in range(1, w - 1):
                if img[i, j] == 0:
                    continue
                neigh = n(i, j)
                B = sum(neigh)
                if 2 <= B <= 6:
                    A = sum([1 for k in range(8) if neigh[k] == 0 and neigh[(k + 1) % 8] == 1])
                    if A == 1:
                        if step == 1:
                            ok = neigh[0] * neigh[2] * neigh[4] == 0 and neigh[2] * neigh[4] * neigh[6] == 0
                        else:
                            ok = neigh[0] * neigh[2] * neigh[6] == 0 and neigh[0] * neigh[4] * neigh[6] == 0
                        if ok:
                            mark[i, j] = 1
        img[mark > 0] = 0
        return np.any(mark)

    while True:
        if not iterate(1) and not iterate(2):
            break
    return img * 255


# ------------------------------------------------------------
# 4. 端点检测
# ------------------------------------------------------------
def _endpoints(skel: np.ndarray) -> List[Tuple[int, int]]:
    skel = skel.copy()
    h, w = skel.shape
    pts = []
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            if skel[i, j] == 0:
                continue
            neigh = skel[i - 1:i + 2, j - 1:j + 2]
            if np.sum(neigh == 255) == 2:
                pts.append((j, i))
    return pts


# ------------------------------------------------------------
# 5. 断点缝合
# ------------------------------------------------------------
def _bridge_gaps(bin_img: np.ndarray, max_gap: int = 12) -> np.ndarray:
    skel = _thinning_zs(bin_img)
    pts = _endpoints(skel)
    if len(pts) < 2:
        return skel

    pts = np.array(pts)
    dist = np.linalg.norm(pts[:, None] - pts[None], axis=2)
    mask = (dist <= max_gap) & (dist > 0)
    for i, j in zip(*np.where(mask)):
        if i < j:
            cv2.line(skel, tuple(pts[i]), tuple(pts[j]), 255, 1)

    return _thinning_zs(skel)


# ------------------------------------------------------------
# 6. 端点配对
# ------------------------------------------------------------
def _pair_endpoints(skel: np.ndarray) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    num_labels, labels = cv2.connectedComponents(skel, connectivity=8)
    pairs = []
    for lab in range(1, num_labels):
        mask = (labels == lab).astype(np.uint8) * 255
        pts = _endpoints(mask)
        if len(pts) < 2:
            continue
        pts = np.array(pts)
        dist = np.linalg.norm(pts[:, None] - pts[None], axis=2)
        i, j = np.unravel_index(np.argmax(dist), dist.shape)
        if abs(pts[i, 0] - pts[j, 0]) + abs(pts[i, 1] - pts[j, 1]) < 40:
            continue
        pairs.append((tuple(pts[i]), tuple(pts[j])))
    return pairs


# ----------------------------------------------------------
# 7. 带严格阈值控制的导线合并
# ----------------------------------------------------------
def merge_wires_with_threshold(
        pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]],
        max_dist: int = 40
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    只在严格的距离阈值内连接导线端点
    确保不会错误连接距离过远的导线
    """
    if len(pairs) <= 1:
        return pairs

    # 收集所有端点
    all_endpoints = []
    for i, (start, end) in enumerate(pairs):  # 修复：使用enumerate获取索引
        all_endpoints.extend([(start, 'start', i), (end, 'end', i)])

    # 找到所有可能的连接对（不同导线的端点）
    potential_connections = []

    for i in range(len(all_endpoints)):
        for j in range(i + 1, len(all_endpoints)):
            pt1, type1, wire_idx1 = all_endpoints[i]
            pt2, type2, wire_idx2 = all_endpoints[j]

            # 只连接不同导线的端点
            if wire_idx1 == wire_idx2:
                continue

            distance = math.dist(pt1, pt2)

            # 严格的距离检查：必须在阈值范围内
            if distance <= max_dist:
                potential_connections.append({
                    'distance': distance,
                    'point1': pt1,
                    'point2': pt2,
                    'wire_idx1': wire_idx1,
                    'wire_idx2': wire_idx2,
                    'type1': type1,
                    'type2': type2
                })

    # 按距离排序，优先连接最近的
    potential_connections.sort(key=lambda x: x['distance'])

    # 执行连接
    connected_wires = set()
    merged_pairs = []

    for conn in potential_connections:
        wire_idx1, wire_idx2 = conn['wire_idx1'], conn['wire_idx2']

        # 检查这两个导线是否已经被连接过
        if wire_idx1 in connected_wires or wire_idx2 in connected_wires:
            continue

        # 获取两个导线的原始端点
        wire1 = pairs[wire_idx1]
        wire2 = pairs[wire_idx2]

        # 确定每个导线要保留的端点（未连接的那个端点）
        if conn['type1'] == 'start':
            wire1_other = wire1[1]  # 保留终点
        else:
            wire1_other = wire1[0]  # 保留起点

        if conn['type2'] == 'start':
            wire2_other = wire2[1]  # 保留终点
        else:
            wire2_other = wire2[0]  # 保留起点

        # 创建新的连接导线
        new_wire = (wire1_other, wire2_other)
        merged_pairs.append(new_wire)

        # 标记这两个导线为已连接
        connected_wires.add(wire_idx1)
        connected_wires.add(wire_idx2)

    # 添加未连接的导线
    for i, wire in enumerate(pairs):
        if i not in connected_wires:
            merged_pairs.append(wire)

    return merged_pairs


# ----------------------------------------------------------
# 8. 保守连接策略（更安全）
# ----------------------------------------------------------
def merge_wires_conservative(
        pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]],
        max_dist: int = 40
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    保守的连接策略：
    只在端点距离非常近且方向一致的情况下才连接
    """
    if len(pairs) <= 1:
        return pairs

    # 这里可以添加方向一致性检查等更严格的条件
    # 当前先使用基本的距离阈值

    return merge_wires_with_threshold(pairs, max_dist)


detect_wire_endpoints("D:\\test\\7.jpg",((15, 70, 50), (40, 255, 255)),'red')
