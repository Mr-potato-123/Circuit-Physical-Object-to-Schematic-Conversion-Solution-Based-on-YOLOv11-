from ultralytics import YOLO
from typing import Tuple, List

# 类别索引到名称的映射
CLASS_NAMES = {
    0: "R_box",
    1: "G",
    2: "V_s",
    3: "S_G",
    4: "S_rev",
    5: "R_x"
}


def get_element_location(image_path: str) -> List[Tuple[Tuple[int, int, int, int], str]]:
    """
    对单张图片做推理，返回检测到的全部目标的位置与类别。

    返回格式：
        [
            ((x1, y1, x2, y2), class_name),
            ...
        ]
    """
    results = YOLO("best.pt").predict(
        source=image_path,
        imgsz=640,
        conf=0.75,
        verbose=False           # 关闭冗余日志
    )

    if len(results) == 0:       # 没有任何检测结果
        return []

    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return []

    xyxy = boxes.xyxy.cpu().numpy().astype(int)  # (N, 4) 像素坐标
    cls_idx = boxes.cls.cpu().numpy().astype(int)  # (N,)

    output: List[Tuple[Tuple[int, int, int, int], str]] = []
    for (x1, y1, x2, y2), idx in zip(xyxy, cls_idx):
        class_name = CLASS_NAMES.get(idx, f"unknown_{idx}")
        output.append(((x1, y1, x2, y2), class_name))

    return output




def demo(filename):
    model = YOLO("best.pt")
    results = model.predict(source = filename,
              project = "predict",
             save=True,save_txt = True,save_conf = True,exist_ok = True, imgsz=640, conf=0.75)

    print(results)
    return

