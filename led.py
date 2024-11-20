import tkinter as tk

class LED(tk.Canvas):
    """LED指示灯"""
    def __init__(self, master, size=20, color='red', label="", **kwargs):
        # 确保背景透明
        kwargs['bg'] = 'black'  # 设置画布背景为黑色
        kwargs['highlightthickness'] = 0  # 移除画布边框
        super().__init__(master, width=size, height=size+20, **kwargs)
        self.size = size
        self.color = color
        self.label = label
        self.is_on = False
        self.is_blinking = False
        self.blink_state = False
        self.blink_interval = 800  # 增加闪烁间隔到800ms
        
        # 绘制LED标签（使用透明背景）
        if label:
            self.create_text(size//2, size+10, text=label, 
                           fill='white', anchor='center')
        
        # 初始绘制
        self._draw_led(False)
        
    def _draw_led(self, on):
        """绘制LED"""
        self.delete("led")
        color = self.color if on else '#331111'  # 暗色
        # 绘制LED主体
        self.create_oval(2, 2, self.size-2, self.size-2, 
                        fill=color, outline='#444444', tags="led")
        # 添加高光效果
        if on:
            self.create_oval(5, 5, self.size//2, self.size//2, 
                           fill='#ffffff', stipple='gray50', tags="led")
            
    def turn_on(self):
        """打开LED"""
        self.is_on = True
        self.is_blinking = False
        self._draw_led(True)
        
    def turn_off(self):
        """关闭LED"""
        self.is_on = False
        self.is_blinking = False
        self._draw_led(False)
        
    def blink(self):
        """开始闪烁"""
        self.is_blinking = True
        self._blink()
        
    def _blink(self):
        """闪烁处理"""
        if self.is_blinking:
            self.blink_state = not self.blink_state
            self._draw_led(self.blink_state)
            self.after(self.blink_interval, self._blink)  # 使用较长的闪烁间隔