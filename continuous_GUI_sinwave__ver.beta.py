import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from scipy.signal import lfilter, butter
import sounddevice as sd # type: ignore
import threading
import time

# 參數設定
fs = 44100            # 取樣頻率 (Hz)
duration = 1          # 持續時間 (秒)
head_width = 0.2      # 頭部寬度 (米)
sound_speed = 343     # 聲速 (米/秒)
frequency = 440       # 正弦波頻率 (Hz)
num_frames = int(fs * duration)

# 生成時間軸
t = np.linspace(0, duration, num_frames, endpoint=False)

# 生成正弦波信號
signal = 0.5 * np.sin(2 * np.pi * frequency * t)

# 初始化左右耳信號
left_signal = np.zeros(num_frames)
right_signal = np.zeros(num_frames)

# 改進的 HRTF 濾波器（前方低通、後方高通）
b_front, a_front = butter(2, 0.8, btype='low')  # 前方低通
b_back, a_back = butter(2, 0.2, btype='high')   # 後方高通

# 用來記錄軌跡的列表
path = []

# 記錄 Circle 是否繼續運行的標誌
is_circle_running = False

# 更新音訊信號的函數
def update_audio(x_pos, y_pos, z_pos):
    left_signal[:] = 0
    right_signal[:] = 0

    # 計算聲源和聽者的距離
    distance = np.hypot(np.hypot(x_pos, y_pos), z_pos)

    # 基於距離進行衰減
    gain = 1 / (distance ** 2)  # 距離衰減 (反比平方律)

    # 改進的 ILD 和 ITD 計算
    angle_rad = np.arctan2(y_pos, x_pos)

    # 計算 ITD，放大延遲效果
    itd = (head_width * np.sin(angle_rad)) / sound_speed
    itd_samples = int(itd * fs * 10)  # 放大 ITD 延遲 10 倍

    # 強化前後區別，強化聲源在前方或後方時的音效
    if y_pos >= 0:  # 聲源在前方
        # 前方的增益差異增強
        left_gain = gain * (0.5 - 0.5 * np.cos(angle_rad))  # 前方左耳增益
        right_gain = gain * (0.5 + 0.5 * np.cos(angle_rad))  # 前方右耳增益
        
        # 前方音效強化（更多的低頻濾波器處理）
        filter_b, filter_a = b_front, a_front
    else:  # 聲源在後方
        left_gain = gain * (0.8 - 0.8 * np.cos(angle_rad))  # 後方左耳增益（增強）
        right_gain = gain * (0.8 + 0.8 * np.cos(angle_rad))  # 後方右耳增益（增強）
        # 後方音效強化（加強高頻）
        filter_b, filter_a = b_back, a_back

    # 根據距離處理增益差異，避免聲音瞬間切換
    if distance < 0.5:  # 當距離很近時，減少增益差異
        left_gain = gain * 0.5
        right_gain = gain * 0.5

    for i in range(num_frames):
        # 計算 Y軸的影響：前後聲音的濾波處理
        filtered_signal = lfilter(filter_b, filter_a, [signal[i]])[0]

        # 加入 ITD（平滑過渡）
        if itd_samples > 0:
            if i + itd_samples < num_frames:
                left_signal[i + itd_samples] += filtered_signal * left_gain
                right_signal[i] += filtered_signal * right_gain
        else:
            if i - itd_samples < num_frames:
                right_signal[i - itd_samples] += filtered_signal * right_gain
                left_signal[i] += filtered_signal * left_gain

    stereo_signal = np.vstack((left_signal, right_signal)).T
    return stereo_signal  # 返回音訊信號

# 初始化位置
initial_x, initial_y, initial_z = 0.0, 0.0, 0.0

# 建立 3D 圖形
fig = plt.figure(figsize=(10, 6))
ax = fig.add_subplot(111, projection='3d')
source_plot, = ax.plot([], [], [], 'ro', label='Sound Source')
listener_plot = ax.scatter(0, 0, 0, color='blue', marker='o', label='Listener')

ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)
ax.set_zlim(-2, 2)
ax.set_xlabel('X Position')
ax.set_ylabel('Y Position')
ax.set_zlabel('Z Position')
ax.legend()

# 滑桿介面
ax_x = plt.axes([0.25, 0.1, 0.65, 0.03])
ax_y = plt.axes([0.25, 0.05, 0.65, 0.03])
ax_z = plt.axes([0.25, 0.0, 0.65, 0.03])

slider_x = Slider(ax_x, 'X Position', -2, 2, valinit=initial_x)
slider_y = Slider(ax_y, 'Y Position', -2, 2, valinit=initial_y)
slider_z = Slider(ax_z, 'Z Position', -2, 2, valinit=initial_z)

# 播放音訊的函數，使用 threading 以避免阻塞 GUI
def play_audio(event):
    def play_in_thread():
        x_pos = slider_x.val
        y_pos = slider_y.val
        z_pos = slider_z.val
        source_plot.set_data([x_pos], [y_pos])
        source_plot.set_3d_properties([z_pos])
        plt.draw()
        
        stereo_signal = update_audio(x_pos, y_pos, z_pos)
        sd.play(stereo_signal, samplerate=fs)

    threading.Thread(target=play_in_thread).start()

# 重置位置的函數
def reset_position(event):
    slider_x.reset()
    slider_y.reset()
    slider_z.reset()

# 播放按鈕
button_ax = plt.axes([0.8, 0.9, 0.1, 0.04])
button = Button(button_ax, 'Play')
button.on_clicked(play_audio)

# 重置按鈕
reset_ax = plt.axes([0.8, 0.85, 0.1, 0.04])
reset_button = Button(reset_ax, 'Reset')
reset_button.on_clicked(reset_position)

# Circle 按鈕，讓音源轉圈
def circle_audio(event):
    global is_circle_running
    is_circle_running = True  # 開始繞圈
    def circle_in_thread():
        radius = 1.0  # 圓的半徑
        angle = 0.0
        while angle < 2 * np.pi and is_circle_running:  # 檢查是否要停止
            x_pos = radius * np.cos(angle)
            y_pos = radius * np.sin(angle)
            z_pos = 0  # 可以增加 Z 軸變化以讓音源在三維空間繞圈
            source_plot.set_data([x_pos], [y_pos])
            source_plot.set_3d_properties([z_pos])
            plt.draw()

            # 播放音訊並稍作停頓
            stereo_signal = update_audio(x_pos, y_pos, z_pos)
            sd.play(stereo_signal, samplerate=fs)
            
            # 減少停頓時間以縮短繞圈的延遲
            time.sleep(1)

            angle += 0.2  # 更新角度，使其循環

    threading.Thread(target=circle_in_thread).start()

# STOP 按鈕，停止音源繞圈
def stop_circle(event):
    global is_circle_running
    is_circle_running = False  # 停止繞圈

# Circle 按鈕
circle_ax = plt.axes([0.8, 0.8, 0.1, 0.04])
circle_button = Button(circle_ax, 'Circle')
circle_button.on_clicked(circle_audio)

# STOP 按鈕
stop_ax = plt.axes([0.8, 0.75, 0.1, 0.04])
stop_button = Button(stop_ax, 'Stop')
stop_button.on_clicked(stop_circle)

plt.show()
