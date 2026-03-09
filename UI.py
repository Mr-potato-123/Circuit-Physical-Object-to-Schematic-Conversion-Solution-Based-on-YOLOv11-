import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
                             QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QPainter, QPen, QColor

from netlist import get_circuit_connections, print_connections_summary
from show import FastDrawer


class AnalysisThread(QThread):
    """分析线程，避免界面卡顿"""
    progress_signal = pyqtSignal(int, str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            self.progress_signal.emit(10, "正在检测元件...")
            from inferrence import get_element_location
            elements = get_element_location(self.image_path)
            self.progress_signal.emit(30, f"检测到 {len(elements)} 个元件")

            self.progress_signal.emit(40, "正在检测导线端点...")
            from get_endpoints import get_endpoints
            endpoints = get_endpoints(self.image_path)
            self.progress_signal.emit(60, f"检测到 {len(endpoints)} 条导线")

            self.progress_signal.emit(70, "分析连接关系...")
            connection_data = get_circuit_connections(self.image_path)

            self.progress_signal.emit(90, "生成电路图数据...")
            # 使用修改后的FastDrawer
            drawer = FastDrawer(connection_data)
            circuit_data = drawer.get_simple_circuit_data()

            connection_data['circuit_data'] = circuit_data
            connection_data['original_image'] = self.image_path

            self.progress_signal.emit(100, "分析完成！")
            self.result_signal.emit(connection_data)

        except Exception as e:
            self.error_signal.emit(str(e))


class CircuitWidget(QWidget):
    """自定义电路图绘制部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.circuit_data = None
        self.setMinimumSize(600, 600)
        self.setStyleSheet("background-color: white; border: 1px solid gray;")

    def set_circuit_data(self, circuit_data):
        self.circuit_data = circuit_data
        self.update()

    def paintEvent(self, event):
        if not self.circuit_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算缩放和偏移
        width, height = self.width(), self.height()

        # 绘制元件
        for element in self.circuit_data['elements']:
            x = element['x'] * 20 + width / 2
            y = element['y'] * 20 + height / 2
            w = element['width'] * 20
            h = element['height'] * 20

            # 绘制矩形
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(Qt.white)
            painter.drawRect(int(x - w / 2), int(y - h / 2), int(w), int(h))

            # 绘制文本
            painter.setPen(Qt.black)
            painter.drawText(int(x - w / 2), int(y - h / 2), int(w), int(h),
                             Qt.AlignCenter, element['name'])

        # 绘制连接线
        for wire in self.circuit_data['wires']:
            start_x, start_y = wire['start_point']
            end_x, end_y = wire['end_point']

            start_x = start_x * 20 + width / 2
            start_y = start_y * 20 + height / 2
            end_x = end_x * 20 + width / 2
            end_y = end_y * 20 + height / 2

            painter.setPen(QPen(QColor(wire['color']), 2))
            painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))


class CircuitAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_result = None

    def initUI(self):
        self.setWindowTitle('电路分析系统')
        self.setGeometry(100, 100, 1400, 900)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 顶部控制区域
        control_layout = QHBoxLayout()

        self.select_btn = QPushButton('选择图片')
        self.select_btn.clicked.connect(self.select_image)
        control_layout.addWidget(self.select_btn)

        self.analyze_btn = QPushButton('开始分析')
        self.analyze_btn.clicked.connect(self.analyze_image)
        self.analyze_btn.setEnabled(False)
        control_layout.addWidget(self.analyze_btn)

        self.save_btn = QPushButton('保存结果')
        self.save_btn.clicked.connect(self.save_results)
        self.save_btn.setEnabled(False)
        control_layout.addWidget(self.save_btn)

        main_layout.addLayout(control_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel('准备就绪')
        main_layout.addWidget(self.status_label)

        # 分割区域
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：图像显示
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        left_layout.addWidget(QLabel("原始图像:"))
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.image_label.setMinimumSize(400, 300)
        left_layout.addWidget(self.image_label)

        # 电路图显示
        left_layout.addWidget(QLabel("电路示意图:"))
        self.circuit_widget = CircuitWidget()
        left_layout.addWidget(self.circuit_widget)

        splitter.addWidget(left_widget)

        # 右侧：结果显示
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        right_layout.addWidget(QLabel("分析结果:"))

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self.result_text)

        splitter.addWidget(right_widget)
        splitter.setSizes([800, 400])

        main_layout.addWidget(splitter)

        self.image_path = None

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择电路图片", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tif)"
        )

        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
            self.analyze_btn.setEnabled(True)
            self.status_label.setText(f"已选择: {os.path.basename(file_path)}")

    def analyze_image(self):
        if not self.image_path:
            QMessageBox.warning(self, "警告", "请先选择图片！")
            return

        self.analyze_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("开始分析...")

        # 启动分析线程
        self.analysis_thread = AnalysisThread(self.image_path)
        self.analysis_thread.progress_signal.connect(self.update_progress)
        self.analysis_thread.result_signal.connect(self.show_results)
        self.analysis_thread.error_signal.connect(self.handle_error)
        self.analysis_thread.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def show_results(self, result_data):
        self.current_result = result_data
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

        # 显示电路图
        if 'circuit_data' in result_data:
            self.circuit_widget.set_circuit_data(result_data['circuit_data'])

        # 显示文本结果
        result_text = self.format_results(result_data)
        self.result_text.setPlainText(result_text)

        self.status_label.setText("分析完成！")

    def format_results(self, result_data):
        """格式化结果显示"""
        text = "电路分析结果\n"
        text += "=" * 50 + "\n\n"

        text += "检测到的元件:\n"
        for elem in result_data['elements']:
            text += f"  • {elem}\n"

        text += "\n连接关系:\n"
        for elem, connected in sorted(result_data['connections'].items()):
            if connected:
                text += f"  {elem} → {', '.join(sorted(connected))}\n"

        text += "\n导线连接:\n"
        for i, wire in enumerate(result_data['wires'], 1):
            text += f"  导线{i}: {' ↔ '.join(wire)}\n"

        return text

    def handle_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "分析错误", f"分析过程中出现错误:\n{error_msg}")
        self.status_label.setText("分析失败")

    def save_results(self):
        if not self.current_result:
            QMessageBox.warning(self, "警告", "没有可保存的结果！")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "circuit_analysis.txt", "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.format_results(self.current_result))
                QMessageBox.information(self, "成功", "结果已保存！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = CircuitAnalyzerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()