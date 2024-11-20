import tkinter as tk

class DigitalDisplay(tk.Canvas):
    """数码管显示器"""
    def __init__(self, master, width=200, height=40, title="", display_type="time", size_factor=1.0, **kwargs):
        # 增加 size_factor 参数来控制显示大小
        super().__init__(master, width=width, height=height+20, bg='black', **kwargs)
        self.segments = {
            # 每个数字的七段显示配置 (上、右上、右下、下、左下、左上、中)
            '0': (1,1,1,1,1,1,0),
            '1': (0,1,1,0,0,0,0),
            '2': (1,1,0,1,1,0,1),
            '3': (1,1,1,1,0,0,1),
            '4': (0,1,1,0,0,1,1),
            '5': (1,0,1,1,0,1,1),
            '6': (1,0,1,1,1,1,1),
            '7': (1,1,1,0,0,0,0),
            '8': (1,1,1,1,1,1,1),
            '9': (1,1,1,1,0,1,1),
            '-': (0,0,0,0,0,0,1),
            ' ': (0,0,0,0,0,0,0),
            ':': None,  # 特殊处理
            'f': (1,0,0,0,1,1,1),  # 添加 'f' 的显示配置
        }
        # 根据 size_factor 调整显示大小
        self.digit_width = int(20 * size_factor)
        self.digit_height = int(35 * size_factor)
        self.segment_width = int(3 * size_factor)
        self.spacing = int(5 * size_factor)
        
        # 根据显示类型设置颜色
        self.display_type = display_type
        self.color = '#00ff00' if display_type == "track" else '#ff0000'  # 绿色用于音轨，红色用于时间
        
        # 添加标题和显示类型标记
        self.title = title
        if title:
            title_text = f"{title} ({'音轨' if display_type == 'track' else '时间'})"
            self.create_text(10, 10, text=title_text, fill='white', anchor='w')
        
    def _draw_segment(self, x, y, segment_type, active):
        """绘制单个段"""
        if not active:
            return
            
        if segment_type in ('top', 'middle', 'bottom'):
            # 水平段
            points = [
                (x + self.segment_width, y),
                (x + self.digit_width - self.segment_width, y),
                (x + self.digit_width - self.segment_width*2, y + self.segment_width),
                (x + self.segment_width*2, y + self.segment_width),
            ]
        else:
            # 垂直段
            points = [
                (x, y + self.segment_width),
                (x + self.segment_width, y),
                (x + self.segment_width, y + self.digit_height//2 - self.segment_width),
                (x, y + self.digit_height//2),
            ]
            
        self.create_polygon(points, fill=self.color, outline=self.color)
        
    def _draw_digit(self, x, y, digit):
        """绘制单个数字"""
        if digit == ':':
            # 绘制冒号
            r = self.segment_width
            y_middle = y + self.digit_height//2
            self.create_oval(x, y_middle-10-r, x+2*r, y_middle-10+r, 
                           fill=self.color, outline=self.color)
            self.create_oval(x, y_middle+10-r, x+2*r, y_middle+10+r, 
                           fill=self.color, outline=self.color)
            return
            
        segments = self.segments.get(digit, self.segments[' '])
        if segments:
            # 绘制七段
            positions = [
                ('top', x, y),  # 上
                ('right-top', x + self.digit_width - self.segment_width, y),  # 右上
                ('right-bottom', x + self.digit_width - self.segment_width, 
                 y + self.digit_height//2),  # 右下
                ('bottom', x, y + self.digit_height),  # 下
                ('left-bottom', x, y + self.digit_height//2),  # 左下
                ('left-top', x, y),  # 左上
                ('middle', x, y + self.digit_height//2),  # 中
            ]
            
            for (segment_type, seg_x, seg_y), active in zip(positions, segments):
                self._draw_segment(seg_x, seg_y, segment_type, active)
                
    def display(self, text):
        """显示文本，支持帧显示"""
        self.delete('all')  # 清除画布
        
        # 重新绘制标题
        if self.title:
            self.create_text(10, 10, text=self.title, fill='white', anchor='w')
            
        x = 5
        y = 20  # 调整起始y坐标，为标题留出空间
        
        # 处理TMSF格式 (分:秒:帧)
        if text != "--:--:--" and ':' in text:
            parts = text.split(':')
            if len(parts) >= 3:  # 如果有帧信息
                minutes, seconds, frames = parts[:3]
                # 显示分和秒
                for char in f"{minutes}:{seconds}":
                    self._draw_digit(x, y, char)
                    x += self.digit_width + self.spacing
                
                # 添加一个小间隔
                x += self.spacing
                
                # 显示帧数和'f'标识
                for char in frames:
                    self._draw_digit(x, y, char)
                    x += self.digit_width + self.spacing
                self._draw_digit(x, y, 'f')
            else:
                # 如果没有帧信息，按原样显示
                for char in text:
                    self._draw_digit(x, y, char)
                    x += self.digit_width + self.spacing
        else:
            # 显示普通文本
            for char in text:
                self._draw_digit(x, y, char)
                x += self.digit_width + self.spacing