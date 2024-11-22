from flask import Flask, render_template, request, send_file, after_this_request
import os
from werkzeug.utils import secure_filename
import cv2
from PIL import Image, ImageDraw, ImageOps, ImageFont
import tempfile
import numpy as np
from argparse import Namespace
import shutil
import time

app = Flask(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 配置字体路径
FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSansMono-Bold.ttf')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi'}

@app.route('/')
def index():
    return render_template('index.html')

def convert_image_to_ascii_image(input_path, output_path, mode, background, num_cols):
    if mode == "simple":
        CHAR_LIST = '@%#*+=-:. '
    else:
        CHAR_LIST = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    
    if background == "white":
        bg_code = 255
    else:
        bg_code = 0

    # 使用更大的字体大小
    try:
        font = ImageFont.truetype(FONT_PATH, size=12)
    except Exception as e:
        print(f"无法加载字体文件: {e}")
        font = ImageFont.load_default()
    
    image = cv2.imread(input_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    height, width = image.shape
    cell_width = width / num_cols
    cell_height = cell_width  # 修改为1:1的比例
    num_rows = int(height / cell_height)
    
    if num_cols > width or num_rows > height:
        cell_width = 6
        cell_height = 6  # 保持1:1比例
        num_cols = int(width / cell_width)
        num_rows = int(height / cell_height)
    
    # 获取字符尺寸
    bbox = font.getbbox("A")
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]
    
    # 调整输出图像尺寸
    out_width = char_width * num_cols
    out_height = char_height * num_rows
    
    out_image = Image.new("L", (out_width, out_height), bg_code)
    draw = ImageDraw.Draw(out_image)
    
    num_chars = len(CHAR_LIST)
    
    # 逐行绘制字符
    for i in range(num_rows):
        for j in range(num_cols):
            # 计算当前区域的平均亮度
            cell = image[int(i * cell_height):min(int((i + 1) * cell_height), height),
                        int(j * cell_width):min(int((j + 1) * cell_width), width)]
            avg = int(np.mean(cell))
            char_idx = min(int(avg * num_chars / 255), num_chars - 1)
            
            # 计算字符位置
            x = j * char_width
            y = i * char_height
            
            # 绘制字符
            draw.text((x, y), CHAR_LIST[char_idx], fill=255 - bg_code, font=font)
    
    # 裁剪图像
    if background == "white":
        cropped_image = ImageOps.invert(out_image).getbbox()
    else:
        cropped_image = out_image.getbbox()
    
    if cropped_image:
        out_image = out_image.crop(cropped_image)
    
    out_image.save(output_path)

def convert_image_to_ascii_text(input_path, output_path, mode, num_cols):
    if mode == "simple":
        CHAR_LIST = '@%#*+=-:. '
    else:
        CHAR_LIST = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    
    image = cv2.imread(input_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    height, width = image.shape
    cell_width = width / num_cols
    cell_height = 2 * cell_width
    num_rows = int(height / cell_height)
    
    num_chars = len(CHAR_LIST)
    
    with open(output_path, 'w') as f:
        for i in range(num_rows):
            for j in range(num_cols):
                cell = image[int(i * cell_height):min(int((i + 1) * cell_height), height),
                        int(j * cell_width):min(int((j + 1) * cell_width), width)]
                avg = int(np.mean(cell))
                char_idx = min(int(avg * num_chars / 255), num_chars - 1)
                f.write(CHAR_LIST[char_idx])
            f.write('\n')

def convert_video_to_ascii_bw(input_path, output_path, mode, background, num_cols, fps):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return False
    
    if fps == 0:
        fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    # 读取第一帧来获取尺寸
    ret, frame = cap.read()
    if not ret:
        return False
    
    # 重置视频
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    # 创建临时图像来获取输出尺寸
    temp_img_path = os.path.join(UPLOAD_FOLDER, 'temp.jpg')
    cv2.imwrite(temp_img_path, frame)
    convert_image_to_ascii_image(temp_img_path, temp_img_path, mode, background, num_cols)
    temp_img = cv2.imread(temp_img_path)
    height, width = temp_img.shape[:2]
    os.remove(temp_img_path)
    
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (width, height))
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 转换每一帧
        temp_frame_path = os.path.join(UPLOAD_FOLDER, 'temp_frame.jpg')
        cv2.imwrite(temp_frame_path, frame)
        convert_image_to_ascii_image(temp_frame_path, temp_frame_path, mode, background, num_cols)
        ascii_frame = cv2.imread(temp_frame_path)
        out.write(ascii_frame)
        os.remove(temp_frame_path)
    
    cap.release()
    out.release()
    return True

def convert_video_to_ascii_color(input_path, output_path, mode, background, num_cols, fps):
    if mode == "simple":
        CHAR_LIST = '@%#*+=-:. '
    else:
        CHAR_LIST = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    
    cap = cv2.VideoCapture(input_path)
    if not fps:
        fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    ret, frame = cap.read()
    if not ret:
        return False
    
    height, width = frame.shape[:2]
    cell_width = width / num_cols
    cell_height = 2 * cell_width
    num_rows = int(height / cell_height)
    
    try:
        font = ImageFont.truetype(FONT_PATH, size=12)
    except Exception as e:
        print(f"无法加载字体文件: {e}")
        font = ImageFont.load_default()
    
    bbox = font.getbbox("A")
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]
    
    out_width = char_width * num_cols
    out_height = 2 * char_height * num_rows
    
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (out_width, out_height))
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        out_image = Image.new("RGB", (out_width, out_height), (0,0,0) if background == "black" else (255,255,255))
        draw = ImageDraw.Draw(out_image)
        
        for i in range(num_rows):
            for j in range(num_cols):
                cell_gray = gray[int(i * cell_height):min(int((i + 1) * cell_height), height),
                            int(j * cell_width):min(int((j + 1) * cell_width), width)]
                cell_color = frame[int(i * cell_height):min(int((i + 1) * cell_height), height),
                             int(j * cell_width):min(int((j + 1) * cell_width), width)]
                avg_gray = int(np.mean(cell_gray))
                avg_color = tuple(map(int, np.mean(np.mean(cell_color, axis=0), axis=0)))
                char_idx = min(int(avg_gray * len(CHAR_LIST) / 255), len(CHAR_LIST) - 1)
                draw.text((j * char_width, i * char_height), CHAR_LIST[char_idx], 
                         fill=avg_color, font=font)
        
        frame_array = np.array(out_image)
        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
        out.write(frame_array)
    
    cap.release()
    out.release()
    return True

def convert_image_to_ascii_color(input_path, output_path, mode, background, num_cols):
    if mode == "simple":
        CHAR_LIST = '@%#*+=-:. '
    else:
        CHAR_LIST = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
    
    if background == "white":
        bg_code = (255, 255, 255)
    else:
        bg_code = (0, 0, 0)

    try:
        font = ImageFont.truetype(FONT_PATH, size=12)
    except Exception as e:
        print(f"无法加载字体文件: {e}")
        font = ImageFont.load_default()
    
    image = cv2.imread(input_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # 转换为RGB颜色空间
    
    height, width, _ = image.shape
    cell_width = width / num_cols
    cell_height = 2 * cell_width
    num_rows = int(height / cell_height)
    
    if num_cols > width or num_rows > height:
        cell_width = 6
        cell_height = 12
        num_cols = int(width / cell_width)
        num_rows = int(height / cell_height)
    
    bbox = font.getbbox("A")
    char_width = bbox[2] - bbox[0]
    char_height = bbox[3] - bbox[1]
    
    out_width = char_width * num_cols
    out_height = 2 * char_height * num_rows
    
    out_image = Image.new("RGB", (out_width, out_height), bg_code)
    draw = ImageDraw.Draw(out_image)
    
    num_chars = len(CHAR_LIST)
    
    for i in range(num_rows):
        for j in range(num_cols):
            # 获取当前单元格的图像部分
            cell = image[int(i * cell_height):min(int((i + 1) * cell_height), height),
                        int(j * cell_width):min(int((j + 1) * cell_width), width)]
            
            # 计算平均颜色
            avg_color = tuple(map(int, np.mean(np.mean(cell, axis=0), axis=0)))
            
            # 计算灰度值来选择字符
            gray = np.mean(cell)
            char_idx = min(int(gray * num_chars / 255), num_chars - 1)
            
            # 绘制彩色字符
            draw.text((j * char_width, i * char_height), 
                     CHAR_LIST[char_idx], 
                     fill=avg_color, 
                     font=font)
    
    # 裁剪图像
    cropped_image = out_image.getbbox()
    out_image = out_image.crop(cropped_image)
    out_image.save(output_path)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """处理文件下载请求"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    # 获取文件的MIME类型
    mime_type = 'application/octet-stream'  # 默认
    if filename.endswith('.txt'):
        mime_type = 'text/plain'
    elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
        mime_type = 'image/' + filename.rsplit('.', 1)[1].lower()
    elif filename.endswith(('.mp4', '.avi')):
        mime_type = 'video/' + filename.rsplit('.', 1)[1].lower()

    # 设置下载的文件名
    download_name = 'ascii_' + filename

    try:
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=True,  # 这会触发下载而不是在浏览器中打开
            download_name=download_name
        )
    except Exception as e:
        return str(e)

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return '没有文件'
    
    file = request.files['file']
    if file.filename == '':
        return '没有选择文件'

    if file and allowed_file(file.filename):
        # 生成唯一的文件名以避免冲突
        original_filename = secure_filename(file.filename)
        filename = f"{os.path.splitext(original_filename)[0]}_{int(time.time())}{os.path.splitext(original_filename)[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # 获取表单参数
            mode = request.form.get('mode', 'simple')
            background = request.form.get('background', 'black')
            num_cols = int(request.form.get('num_cols', 100))
            output_type = request.form.get('output_type', 'ascii_image')
            fps = int(request.form.get('fps', 30))

            # 根据文件类型和输出类型选择不同的转换方法
            is_video = filename.lower().endswith(('.mp4', '.avi'))
            output_filename = f'output_{filename}'
            if is_video:
                output_filename = output_filename.rsplit('.', 1)[0] + '.avi'
            elif output_type == 'ascii_text':
                output_filename = output_filename.rsplit('.', 1)[0] + '.txt'
            else:
                output_filename = output_filename.rsplit('.', 1)[0] + '.png'  # 使用PNG格式保存图片
            
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            if is_video:
                if output_type == 'ascii_video_bw':
                    success = convert_video_to_ascii_bw(filepath, output_path, mode, background, num_cols, fps)
                else:  # ascii_video_color
                    success = convert_video_to_ascii_color(filepath, output_path, mode, background, num_cols, fps)
                if not success:
                    return '视频转换失败'
            else:  # 图片
                if output_type == 'ascii_text':
                    convert_image_to_ascii_text(filepath, output_path, mode, num_cols)
                elif output_type == 'ascii_image_color':
                    convert_image_to_ascii_color(filepath, output_path, mode, background, num_cols)
                else:  # ascii_image
                    convert_image_to_ascii_image(filepath, output_path, mode, background, num_cols)

            # 设置自动清理文件
            @after_this_request
            def cleanup(response):
                try:
                    # 设置一个定时器在30分钟后删除文件
                    def delete_files():
                        time.sleep(1800)  # 30分钟
                        if os.path.exists(filepath):
                            os.remove(filepath)
                        if os.path.exists(output_path):
                            os.remove(output_path)
                    
                    import threading
                    threading.Thread(target=delete_files).start()
                except Exception as e:
                    app.logger.error(f"Error cleaning up files: {e}")
                return response

            return render_template('index.html', result_file=f'/uploads/{output_filename}')

        except Exception as e:
            # 清理文件
            if os.path.exists(filepath):
                os.remove(filepath)
            return f'转换过程中出错: {str(e)}'

    return '不支持的文件类型'

if __name__ == '__main__':
    app.run(debug=True) 