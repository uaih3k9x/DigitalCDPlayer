import tkinter as tk
from tkinter import messagebox
import ctypes
import traceback
from cddb_handler import CDDBHandler
from tkinter import ttk
from display import DigitalDisplay
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from led import LED

class CDPlayer:
    def __init__(self):
        self.mci = ctypes.windll.winmm.mciSendStringW
        self.buffer = ctypes.create_unicode_buffer(128)
        self.current_track = None
        self.is_playing = False
        self.position_buffer = ctypes.create_unicode_buffer(128)
        self.position_command = "status cd position"

    def initialize(self, drive_letter):
        """初始化CD驱动器"""
        try:
            # 确保先关闭现有的CD
            self.mci("close cd", None, 0, None)
            
            # 尝试打开新的CD
            command = f"open {drive_letter}: type cdaudio alias cd wait"
            result = self.mci(command, None, 0, None)
            if result != 0:
                raise Exception(f"无法打开驱动器 {drive_letter}:")
            
            # 设置时间格式
            self.set_time_format("tmsf")
            return True
        except Exception as e:
            print(f"初始化CD失败: {e}")
            return False

    def set_time_format(self, format_type):
        """设置时间格式"""
        result = self.mci(f"set cd time format {format_type}", None, 0, None)
        if result != 0:
            raise Exception(f"设置时间格式失败: {result}")

    def get_cd_info(self):
        """获取CD信息"""
        try:
            # 获取总音轨数
            result = self.mci("status cd number of tracks", self.buffer, 128, None)
            if result != 0 or not self.buffer.value:
                raise Exception("无法获取音轨数量或未检测到CD")
            num_tracks = int(self.buffer.value)

            # 获取CD标识符
            result = self.mci("info cd identity", self.buffer, 128, None)
            if result != 0:
                raise Exception("无法获取CD标识符")
            cd_id = self.buffer.value

            return cd_id, num_tracks
        except Exception as e:
            raise Exception(f"获取CD信息失败: {e}")

    def get_track_length(self, track_number):
        """获取指定音轨的长度"""
        result = self.mci(f"status cd length track {track_number}", self.buffer, 128, None)
        if result != 0:
            raise Exception(f"无法获取音轨 {track_number} 的长度")
        return self.buffer.value

    def play_track(self, track_number):
        """播放指定音轨"""
        try:
            self.stop()
            self.current_track = track_number
            
            # 获取音轨的起始位置
            start_pos_buffer = ctypes.create_unicode_buffer(128)
            result = self.mci(f"status cd position track {track_number}", start_pos_buffer, 128, None)
            if result != 0:
                raise Exception(f"获取音轨起始位置失败: {result}")
                
            # 定位到音轨起始位置
            result = self.mci(f"seek cd to {start_pos_buffer.value}", None, 0, None)
            if result != 0:
                raise Exception(f"定位失败: {result}")
                
            # 开始播放
            result = self.mci("play cd", None, 0, None)
            if result != 0:
                raise Exception(f"播放失败: {result}")
                
            self.is_playing = True
            
        except Exception as e:
            raise Exception(f"播放音轨失败: {e}")

    def stop(self):
        """停止播放"""
        self.mci("stop cd", None, 0, None)
        self.is_playing = False

    def eject(self):
        """弹出CD"""
        self.mci("set cd door open", None, 0, None)

    def get_position(self):
        """获取当前播放位置"""
        if self.is_playing:
            result = self.mci(self.position_command, self.position_buffer, 128, None)
            if result == 0:
                return self.position_buffer.value
        return None

    def get_total_length(self):
        """获取CD总长度"""
        result = self.mci("status cd length", self.buffer, 128, None)
        if result != 0:
            raise Exception("无法获取CD总长度")
        return self.buffer.value

    def get_track_start_position(self, track_number):
        """获取音轨的起始位置"""
        result = self.mci(f"status cd position track {track_number}", self.buffer, 128, None)
        if result != 0:
            raise Exception(f"无法获取音轨 {track_number} 的起始位置")
        return self.buffer.value

    def get_track_end_position(self, track_number):
        """获取音轨的结束位置"""
        # 获取下一个音轨的起始位置作为当前音轨的结束位置
        result = self.mci(f"status cd position track {track_number + 1}", self.buffer, 128, None)
        if result != 0:
            # 如果是最后一个音轨，使用总长度
            result = self.mci("status cd length", self.buffer, 128, None)
            if result != 0:
                raise Exception(f"无法获取音轨 {track_number} 的结束位置")
        return self.buffer.value

    def _calculate_disc_id(self) -> tuple:
        """计算disc_id和相关信息"""
        try:
            # 获取轨道数
            result = self.mci("status cd number of tracks", self.buffer, 128, None)
            if result != 0:
                raise Exception("无法获取音轨数量")
            num_tracks = int(self.buffer.value)
            
            # 获取每个轨道的起始位置和长度
            track_offsets = []
            for i in range(1, num_tracks + 1):
                # 获取轨道起始位置（以帧为单位）
                self.mci(f"status cd position track {i}", self.buffer, 128, None)
                start_pos = self._tmsf_to_frames(self.buffer.value)
                track_offsets.append(start_pos)
            
            # 获取光盘总长度
            self.mci("status cd length", self.buffer, 128, None)
            total_length = self._tmsf_to_frames(self.buffer.value)
            
            # 生成disc_id（简化版本）
            disc_id = f"{num_tracks}-{total_length}"
            for offset in track_offsets:
                disc_id += f"-{offset}"
            
            return disc_id, num_tracks, track_offsets, total_length
            
        except Exception as e:
            print(f"计算disc_id失败: {e}")
            return None, 0, [], 0

    def _tmsf_to_frames(self, tmsf: str) -> int:
        """将TMSF格式转换为帧数"""
        try:
            parts = tmsf.split(':')
            if len(parts) == 3:
                minutes = int(parts[0])
                seconds = int(parts[1])
                frames = int(parts[2])
                return frames + (seconds * 75) + (minutes * 60 * 75)
            return 0
        except:
            return 0

class CDPlayerGUI:
    def __init__(self):
        self.cd_player = CDPlayer()
        self.window = tk.Tk()
        self.window.title("Digital CD Player v1.0")  # 修改标题
        self.window.configure(bg='black')  # 设置窗口背景色
        
        # 初始化变量
        self.track_info = tk.StringVar(value="No CD loaded")
        self.cd_drive = tk.StringVar(value="D")
        self.current_position = tk.StringVar(value="--:--:--")
        self.total_position = tk.StringVar(value="--:--:--")
        self.current_track = tk.StringVar(value="--")
        self.last_position = None
        self.update_interval = 100  # 增加更新间隔到100ms
        self.position_update_count = 0
        self.position_update_threshold = 5
        self.cddb_handler = CDDBHandler()
        self.cd_info = None
        # 添加新的变量用于存储专辑信息
        self.album_info_frame = None
        self.track_list = None
        self.album_info = ""
        self.is_paused = False  # 添加暂停状态标志

        # 创建数码管显示器
        self.current_display = DigitalDisplay(self.window, width=200, height=40, 
                                            title="当前位置", display_type="time")
        self.total_display = DigitalDisplay(self.window, width=200, height=40, 
                                          title="总长度", display_type="time")
        
        # 添加版本信息变量
        self.version_info = "Digital CD Player v1.0"
        self.cddb_info = tk.StringVar(value="等待加载CD信息...")

        self.create_gui()
        self.initialize_cd()
        self.update_position()  # 开始位置更新

    def create_gui(self):
        """创建GUI界面"""
        # 添加版本信息框
        info_frame = tk.LabelFrame(self.window, text="系统信息", bg='black', fg='white', padx=5, pady=5)
        info_frame.pack(fill='x', padx=5, pady=5)
        
        # 版本信息
        version_label = tk.Label(info_frame, text=self.version_info,
                               bg='black', fg='#00ff00', font=('Consolas', 10))
        version_label.pack(anchor='w')
        
        # CDDB信息
        cddb_label = tk.Label(info_frame, textvariable=self.cddb_info,
                             bg='black', fg='#00ff00', font=('Consolas', 10))
        cddb_label.pack(anchor='w')
        
        # 控制按钮和LED区域
        control_frame = tk.Frame(self.window, bg='black')
        control_frame.pack(fill='x', padx=5, pady=5)
        
        # 左侧按钮组
        button_frame = tk.Frame(control_frame, bg='black')
        button_frame.pack(side='left', padx=10)
        
        # 创建按钮和对应的LED
        tk.Button(button_frame, text="Play/Pause", 
                 command=self.toggle_play_pause).pack(side='left', padx=2)
        self.play_led = LED(button_frame, color='green', label="PLAY")
        self.play_led.pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Stop", 
                 command=self.stop_playback).pack(side='left', padx=2)
        self.stop_led = LED(button_frame, color='red', label="STOP")
        self.stop_led.pack(side='left', padx=5)
        
        tk.Button(button_frame, text="Eject", command=self.cd_player.eject).pack(side='left', padx=2)
        
        # 右侧驱动器选择
        drive_frame = tk.Frame(control_frame, bg='black')
        drive_frame.pack(side='right', padx=10)
        tk.Label(drive_frame, text="CD Drive:", bg='black', fg='white').pack(side='left')
        tk.Entry(drive_frame, textvariable=self.cd_drive, width=5).pack(side='left', padx=2)
        tk.Button(drive_frame, text="Load Info", 
                  command=self.initialize_cd).pack(side='left', padx=2)
        
        # 显示区域
        display_frame = tk.Frame(self.window, bg='black')
        display_frame.pack(fill='x', padx=5, pady=10)
        
        # 大号音轨显示
        self.track_display = DigitalDisplay(display_frame, width=150, height=80, 
                                          title="音轨", display_type="track",
                                          size_factor=1.5)  # 增大显示大小
        self.track_display.pack(side='left', padx=10)
        
        # 时间显示
        time_frame = tk.Frame(display_frame, bg='black')
        time_frame.pack(side='left', padx=10)
        self.current_display = DigitalDisplay(time_frame, width=200, height=40, 
                                            title="当前位置", display_type="time")
        self.current_display.pack(pady=2)
        self.total_display = DigitalDisplay(time_frame, width=200, height=40, 
                                          title="总长度", display_type="time")
        self.total_display.pack(pady=2)
        
        # 音轨列表区域
        track_frame = tk.LabelFrame(self.window, text="音轨列表", padx=5, pady=5)
        track_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建音轨列表
        columns = ("track", "time", "title")
        self.track_list = ttk.Treeview(track_frame, columns=columns, show="headings", height=10)
        
        # 设置列标题
        self.track_list.heading("track", text="音轨")
        self.track_list.heading("time", text="时长")
        self.track_list.heading("title", text="标题")
        
        # 设置列宽
        self.track_list.column("track", width=50)
        self.track_list.column("time", width=80)
        self.track_list.column("title", width=300)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(track_frame, orient="vertical", command=self.track_list.yview)
        self.track_list.configure(yscrollcommand=scrollbar.set)
        
        self.track_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def update_position(self):
        """更新播放位置"""
        try:
            if self.cd_player.is_playing:
                # LED状态更新
                self.play_led.turn_on()
                self.stop_led.turn_off()
                
                position = self.cd_player.get_position()
                if position:
                    if position != self.last_position:
                        # 更新当前音轨显示
                        if self.cd_player.current_track:
                            self.track_display.display(f"{self.cd_player.current_track:02d}")
                        
                        # 更新时间显示
                        parts = position.split(':')
                        if len(parts) >= 3:
                            track, minutes, seconds = parts[:3]
                            frames = parts[3] if len(parts) > 3 else "00"
                            
                            minutes = f"{int(minutes):02d}"
                            seconds = f"{int(seconds):02d}"
                            frames = f"{int(frames):02d}"
                            
                            formatted_time = f"{minutes}:{seconds}:{frames}"
                            self.current_display.display(formatted_time)
                        
                        self.last_position = position
                        
                        # 检查是否需要停止播放
                        self.position_update_count += 1
                        if self.position_update_count >= self.position_update_threshold:
                            self.position_update_count = 0
                            
                            if self.cd_player.current_track:
                                try:
                                    end_position = self.cd_player.get_track_end_position(self.cd_player.current_track)
                                    if position >= end_position:
                                        self.cd_player.stop()
                                        self.last_position = None
                                        self.current_display.display("--:--:--")
                                except Exception:
                                    pass
            elif self.is_paused:
                # 暂停状态
                self.play_led.blink()
                self.stop_led.turn_off()
            else:
                # 停止状态
                if self.last_position is not None:
                    self.play_led.turn_off()
                    self.stop_led.turn_on()
                    self.current_display.display("--:--:--")
                    self.track_display.display("--")
                    self.last_position = None
                    self.position_update_count = 0
                    
        except Exception as e:
            print(f"Position update error: {e}")
        finally:
            self.window.after(self.update_interval, self.update_position)

    def initialize_cd(self):
        """加载CD信息"""
        try:
            drive = self.cd_drive.get()
            self.track_info.set("正在读取CD信息...")
            
            if not self.cd_player.initialize(drive):
                raise Exception("CD初始化失败")
            
            self.load_cd_info()
            
        except Exception as e:
            messagebox.showerror("错误", f"初始化CD失败: {str(e)}")
            self.track_info.set("CD加载失败")

    def load_cd_info(self):
        """加载CD信息（带CDDB支持）"""
        try:
            cd_id, num_tracks = self.cd_player.get_cd_info()
            
            # 清空现有列表
            for item in self.track_list.get_children():
                self.track_list.delete(item)
            
            # 获取详细的CD信息用于显示
            disc_id, num_tracks, track_offsets, total_length = self.cd_player._calculate_disc_id()
            
            # 更新CDDB信息显示
            cddb_text = (
                f"CD ID: {disc_id}\n"
                f"音轨数: {num_tracks}\n"
                f"总长度: {total_length} frames"
            )
            
            # 显示专辑信息
            if self.cd_info and self.cd_info.get('tracks'):
                album_info = (
                    f"专辑：{self.cd_info.get('album', '未知专辑')}\n"
                    f"艺术家：{self.cd_info.get('artist', '未知艺术家')}\n"
                )
                cddb_text = album_info + cddb_text
                
                # 使用CDDB信息添加音轨
                for track in self.cd_info['tracks']:
                    track_number = int(track['number'])
                    if track_number <= num_tracks:
                        length = self.cd_player.get_track_length(track_number)
                        self.track_list.insert("", "end", values=(
                            f"{track_number:02d}",
                            length,
                            track['title']
                        ))
            else:
                # 如果没有CDDB信息，显示基本信息    
                for i in range(1, num_tracks + 1):
                    length = self.cd_player.get_track_length(i)
                    self.track_list.insert("", "end", values=(
                        f"{i:02d}",
                        length,
                        f"音轨 {i}"
                    ))
            
            # 更新信息显示
            self.cddb_info.set(cddb_text)

            # 更新CD总长度
            total_length = self.cd_player.get_total_length()
            self.total_display.display(total_length)

        except Exception as e:
            messagebox.showerror("错误", f"加载CD信息失败: {str(e)}")
            traceback.print_exc()

    def play_selected_track(self):
        """播放选中的音轨"""
        try:
            selection = self.track_list.selection()
            if not selection:
                messagebox.showerror("错误", "请先选择一个音轨")
                return
                
            track_number = self.track_list.index(selection[0]) + 1
            self.last_position = None
            
            # 更新音轨显示
            self.track_display.display(f"{track_number:02d}")
            
            track_info = self.cddb_handler.get_track_info(track_number)
            if track_info:
                status_text = (
                    f"{self.album_info}\n"
                    f"正在播放: {track_info.get('title', f'音轨 {track_number}')}"
                )
                self.track_info.set(status_text)
                
            self.cd_player.play_track(track_number)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if not self.cd_player.is_playing and not self.is_paused:
            # 如果当前停止状态，开始播放
            self.play_selected_track()
        elif self.cd_player.is_playing:
            # 如果正在播放，暂停
            self.cd_player.mci("pause cd", None, 0, None)
            self.cd_player.is_playing = False
            self.is_paused = True
            self.play_led.blink()
        else:
            # 如果暂停状态，继续播放
            self.cd_player.mci("resume cd", None, 0, None)
            self.cd_player.is_playing = True
            self.is_paused = False
            self.play_led.turn_on()

    def stop_playback(self):
        """停止播放"""
        self.cd_player.stop()
        self.is_paused = False
        self.play_led.turn_off()
        self.stop_led.turn_on()
        self.current_display.display("--:--:--")
        self.track_display.display("--")
        self.last_position = None

    def run(self):
        """运行程序"""
        self.window.mainloop()

if __name__ == "__main__":
    app = CDPlayerGUI()
    app.run()