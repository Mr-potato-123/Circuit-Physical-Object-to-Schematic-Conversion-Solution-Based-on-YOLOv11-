# show_fast.py （修改版，适合UI集成）
import heapq, random, math
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches

# ---------------- 参数 ----------------
BOX_W, BOX_H = 4.0, 2.0
SAFE = 0.5  # 安全距离
STEP = 1.0  # 步长
MAX_NODES = 5000  # 防止死循环


def snap(x, y):
    return round(x / STEP) * STEP, round(y / STEP) * STEP


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class FastDrawer:
    def __init__(self, net):
        self.elms = net['elements']
        self.conns = net['connections']
        self.wires = [(a, b) for a, b in net['wires']]
        self.pos = {}
        self._layout()
        self.colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                       '#FF1493', '#a65628', '#f781bf', '#999999']
        random.shuffle(self.colors)
        self.wc = {w: self.colors[i % len(self.colors)]
                   for i, w in enumerate(self.wires)}

    # 网格布局（不重叠）
    def _layout(self):
        cols = math.ceil(math.sqrt(len(self.elms)))
        for idx, name in enumerate(self.elms):
            c = idx % cols
            r = idx // cols
            self.pos[name] = (c * (BOX_W + SAFE * 4),
                              -r * (BOX_H + SAFE * 4))

    # 禁区检测
    def _inside(self, p):
        x, y = p
        for x0, y0 in self.pos.values():
            if abs(x - x0) < BOX_W / 2 + SAFE and abs(y - y0) < BOX_H / 2 + SAFE:
                return True
        return False

    # A* 带上限
    def _route(self, start, goal):
        open_heap = [(0, start)]
        came = {start: None}
        g = {start: 0}
        cnt = 0
        while open_heap and cnt < MAX_NODES:
            cnt += 1
            _, cur = heapq.heappop(open_heap)
            if cur == goal:
                break
            for dx, dy in ((STEP, 0), (-STEP, 0), (0, STEP), (0, -STEP)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if self._inside(nxt):
                    continue
                tentative = g[cur] + STEP
                if nxt not in g or tentative < g[nxt]:
                    g[nxt] = tentative
                    came[nxt] = cur
                    heapq.heappush(open_heap, (tentative + dist(nxt, goal), nxt))
        # 回溯
        path = []
        node = goal if goal in came else start
        while node:
            path.append(node)
            node = came.get(node)
        return path[::-1]

    # 端口
    def _port(self, elm, side, idx, total):
        x, y = self.pos[elm]
        w, h = BOX_W / 2, BOX_H / 2
        if side in ('N', 'S'):
            px = x - w + (idx + 1) * BOX_W / (total + 1)
            py = y + h if side == 'N' else y - h
        else:
            px = x + w if side == 'E' else x - w
            py = y - h + (idx + 1) * BOX_H / (total + 1)
        return px, py

    def _side(self, a, b):
        xa, ya = self.pos[a]
        xb, yb = self.pos[b]
        return 'E' if xa < xb else 'W' if xa > xb else 'N' if ya < yb else 'S'

    def create_circuit_figure(self):
        """创建电路图的matplotlib图形对象，不显示"""
        fig, ax = plt.subplots(figsize=(12, 9))
        ax.set_aspect('equal')
        ax.axis('off')

        # 画元件
        for name, (x, y) in self.pos.items():
            rect = plt.Rectangle((x - BOX_W / 2, y - BOX_H / 2),
                                 BOX_W, BOX_H, linewidth=1.2, edgecolor='k', facecolor='w')
            ax.add_patch(rect)
            ax.text(x, y, name, ha='center', va='center', fontsize=9)

        # 画线
        used = {e: {'N': 0, 'S': 0, 'E': 0, 'W': 0} for e in self.elms}
        for a, b in self.wires:
            sa = self._side(a, b)
            sb = self._side(b, a)
            total_a = sum(1 for nb in self.conns[a] if self._side(a, nb) == sa)
            total_b = sum(1 for nb in self.conns[b] if self._side(b, nb) == sb)
            ia = used[a][sa];
            ib = used[b][sb]
            used[a][sa] += 1;
            used[b][sb] += 1

            p1 = self._port(a, sa, ia, total_a)
            p2 = self._port(b, sb, ib, total_b)

            # 垂直退避
            dx0, dy0 = {'N': (0, SAFE), 'S': (0, -SAFE),
                        'E': (SAFE, 0), 'W': (-SAFE, 0)}[sa]
            start = (p1[0] + dx0, p1[1] + dy0)
            dx1, dy1 = {'N': (0, SAFE), 'S': (0, -SAFE),
                        'E': (SAFE, 0), 'W': (-SAFE, 0)}[sb]
            goal = (p2[0] + dx1, p2[1] + dy1)

            path = [start] + self._route(start, goal)[1:-1] + [goal]
            xs, ys = zip(*([p1] + path + [p2]))
            ax.plot(xs, ys, color=self.wc[(a, b)], linewidth=2)

        margin = 1
        xs, ys = zip(*self.pos.values())
        ax.set_xlim(min(xs) - BOX_W - margin, max(xs) + BOX_W + margin)
        ax.set_ylim(min(ys) - BOX_H - margin, max(ys) + BOX_H + margin)
        plt.tight_layout()

        return fig

    def get_simple_circuit_data(self):
        """获取简化的电路数据，用于自定义绘制"""
        circuit_data = {
            'elements': [],
            'wires': []
        }

        # 元件数据
        for name, (x, y) in self.pos.items():
            circuit_data['elements'].append({
                'name': name,
                'x': x,
                'y': y,
                'width': BOX_W,
                'height': BOX_H
            })

        # 连接线数据
        used = {e: {'N': 0, 'S': 0, 'E': 0, 'W': 0} for e in self.elms}
        for a, b in self.wires:
            if a in self.pos and b in self.pos:
                sa = self._side(a, b)
                sb = self._side(b, a)
                total_a = sum(1 for nb in self.conns[a] if self._side(a, nb) == sa)
                total_b = sum(1 for nb in self.conns[b] if self._side(b, nb) == sb)
                ia = used[a][sa];
                ib = used[b][sb]
                used[a][sa] += 1;
                used[b][sb] += 1

                p1 = self._port(a, sa, ia, total_a)
                p2 = self._port(b, sb, ib, total_b)

                circuit_data['wires'].append({
                    'from_element': a,
                    'to_element': b,
                    'start_point': p1,
                    'end_point': p2,
                    'color': self.wc.get((a, b), '#0000FF')
                })

        return circuit_data


def show_circuit(image_path: str):
    """显示电路图（独立使用时的函数）"""
    from netlist import get_circuit_connections
    net = get_circuit_connections(image_path)
    dr = FastDrawer(net)
    fig = dr.create_circuit_figure()
    plt.show()


