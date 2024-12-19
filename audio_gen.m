% 加載 HRIR 數據
data = load('hrir_final_big.mat');

% 提取 HRIR 數據和角度
hrir_left = data.hrir_l;  % 左耳 HRIR
hrir_right = data.hrir_r; % 右耳 HRIR
angles = [-80, -65, -55, -45, -40, -35, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 55, 65, 80];

% 設置移動範圍和速度
start_angle = -180;  % 起始角度
end_angle = 180;     % 終止角度
angle_step = 5;      % 每幀變化的角度
moving_angles = start_angle:angle_step:end_angle;  % 角度序列
%moving_angles = end_angle:-5:start_angle;  % 角度序列
%moving_angles = [-180];
%moving_angles = [-90];
%moving_angles = [0];
%moving_angles = [45];
% 載入音頻信號
[input_audio, fs] = audioread('nl.m4a');

% 計算每段音頻的長度（與角度變化對應）
num_frames = length(moving_angles);  % 總幀數
frame_length = floor(length(input_audio) / num_frames);  % 每幀的樣本數

% 初始化輸出音頻
output_audio = zeros(length(input_audio), 2);

% 初始化圖形
figure;
theta = linspace(0, 2*pi, 100);
plot(cos(theta), sin(theta), 'k--'); % 圓形背景
hold on;
h = scatter(0, 0, 100, 'filled');  % 初始位置
xlim([-1.5, 1.5]);
ylim([-1.5, 1.5]);
grid on;
title('聲源位置');
xlabel('X');
ylabel('Y');

% 處理每一幀音頻
for i = 1:num_frames
    % 獲取當前角度
    current_angle = moving_angles(i);
    
    % 根據角度範圍進行鏡射處理
    if current_angle > 99
        current_angle = 180 - current_angle;
    elseif current_angle < -99
        current_angle = -180 - current_angle;
    elseif current_angle >= 81
        current_angle = 80;
    elseif current_angle <= -81
        current_angle = -80;
    end
    
    % 打印出 current_angle 和 moving_angle
    disp(['Moving angle: ', num2str(moving_angles(i)), ', Current angle: ', num2str(current_angle)]);
    
    % 檢查當前角度是否存在於 angles 中
    [is_found, idx] = ismember(current_angle, angles);
    if is_found
        hrir_l_target = squeeze(hrir_left(idx, 8, :));    % 左耳 HRIR
        hrir_r_target = squeeze(hrir_right(idx, 8, :));   % 右耳 HRIR
    else
        % 使用內插補充找不到的角度
        disp(['Angle ', num2str(current_angle), ' not found in angles! Interpolating...']);
        hrir_l_target = interp1(angles, squeeze(hrir_left(:, 8, :)), current_angle, 'linear', 'extrap');
        hrir_r_target = interp1(angles, squeeze(hrir_right(:, 8, :)), current_angle, 'linear', 'extrap');
    end
    
    % 提取當前幀的音頻
    start_idx = (i-1) * frame_length + 1;
    end_idx = min(i * frame_length, length(input_audio));
    audio_frame = input_audio(start_idx:end_idx, :);  % 直接處理雙聲道音頻

    % 卷積當前幀音頻與 HRIR，使用 'valid' 輸出
    left_output = conv(audio_frame(:,1), hrir_l_target, 'valid');
    right_output = conv(audio_frame(:,2), hrir_r_target, 'valid');

    % 保存到文件
    audiowrite('nl_C.wav', output_audio, fs);
    
    % 計算 'valid' 卷積的結果長度
    valid_length = length(left_output);  
    
    % 計算新索引，確保它們在有效範圍內
    start_idx_valid = start_idx + floor(length(hrir_l_target) / 2);  % 計算偏移量
    end_idx_valid = start_idx_valid + valid_length - 1;

    % 確保索引不會超出範圍
    if end_idx_valid <= length(input_audio)
        output_audio(start_idx_valid:end_idx_valid, 1) = left_output;
        output_audio(start_idx_valid:end_idx_valid, 2) = right_output;
    else
        % 如果超出範圍，可以根據需要處理這些邊界部分（例如，對邊界處進行填充或修正）
        output_audio(start_idx_valid:end_idx, 1) = left_output(1:end_idx - start_idx_valid + 1);
        output_audio(start_idx_valid:end_idx, 2) = right_output(1:end_idx - start_idx_valid + 1);
    end
end

% 創建音頻播放器
player = audioplayer(output_audio, fs);

% 播放音樂並同步更新動畫
play(player);  % 開始播放
frame_time = length(input_audio) / (fs * num_frames); % 每幀播放時間 (秒)

for i = 1:num_frames
    % 計算當前聲源位置
    x_pos = cosd(-(moving_angles(i)-90));  % 計算 X 座標
    y_pos = sind(-(moving_angles(i)-90));  % 計算 Y 座標
    set(h, 'XData', x_pos, 'YData', y_pos);  % 更新散點位置
    drawnow;  % 更新圖形

    % 等待音樂播放到該幀時間
    pause(frame_time); 
end

% 保存到文件
audiowrite('nl_C.wav', output_audio, fs);

% 提示完成
disp('移動聲源模擬完成，音頻已保存為 moving_sound_output_with_visualization.wav');
