import cv2
import numpy as np
from ultralytics import YOLO
import os
from django.conf import settings

# 加载YOLOv8模型
def load_yolov8_model():
    """加载YOLOv8模型"""
    model_path = os.path.join(settings.BASE_DIR, 'best.pt')
    try:
        model = YOLO(model_path)
        return model
    except Exception as e:
        print(f"加载YOLOv8模型失败: {e}")
        return None

# 检测图片
def detect_image(image_file, model):
    """对上传的图片进行目标检测"""
    try:
        print("开始图片检测...")
        
        # 读取图片
        image_bytes = image_file.read()
        print(f"读取图片字节数: {len(image_bytes)}")
        
        nparr = np.frombuffer(image_bytes, np.uint8)
        print("numpy数组创建成功")
        
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        print("OpenCV图像解码成功")
        
        if image is None:
            return None, "无法读取图片"
        
        print(f"图像尺寸: {image.shape}")
        
        # 进行目标检测
        print("开始YOLOv8目标检测...")
        results = model(image)
        print("目标检测完成")
        
        # 绘制检测结果
        annotated_image = results[0].plot()
        print("检测结果绘制完成")
        
        # 转换为base64格式返回
        _, buffer = cv2.imencode('.jpg', annotated_image)
        img_str = buffer.tobytes()
        print("图像编码完成")
        
        # 获取检测结果信息
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    detections.append({
                        'class': result.names[cls],
                        'confidence': round(conf,2),
                        'bbox': box.xyxy[0].tolist()
                    })
        
        print(f"检测到 {len(detections)} 个目标")
        return img_str, detections
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"检测过程中出错: {error_details}")
        return None, f"检测过程中出错: {str(e)}"

def detect_video(video_file, model):
    try:
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # 保存临时视频文件
        temp_video_path = os.path.join(settings.MEDIA_ROOT, 'temp_video.mp4')
        with open(temp_video_path, 'wb') as f:
            for chunk in video_file.chunks():
                f.write(chunk)
        
        # 打开视频文件
        cap = cv2.VideoCapture(temp_video_path)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        
        # 获取视频总帧数
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"视频总帧数: {total_frames}, FPS: {fps}")
        
        frame_count = 0
        detected = False
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            print(f"正在检测第 {frame_count}/{total_frames} 帧...")
            
            # 进行目标检测
            results = model(frame)
            
            # 获取当前帧的检测结果
            current_detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        current_detections.append({
                            'class': result.names[cls],
                            'confidence': conf,
                            'bbox': box.xyxy[0].tolist()
                        })
            
            # 如果当前帧检测到目标，立即返回结果
            if current_detections:
                print(f"第 {frame_count} 帧检测到 {len(current_detections)} 个目标，立即返回结果")
                detected = True
                
                # 绘制检测结果
                annotated_frame = results[0].plot()
                
                # 转换为base64格式返回
                _, buffer = cv2.imencode('.jpg', annotated_frame)
                img_str = buffer.tobytes()
                
                # 格式化检测结果（保留两位小数）
                formatted_detections = []
                for d in current_detections:
                    formatted_detections.append({
                        'class': d['class'],
                        'confidence': round(d['confidence'], 2),
                        'bbox': d['bbox']
                    })
                
                # 释放视频并删除临时文件
                cap.release()
                if os.path.exists(temp_video_path):
                    os.remove(temp_video_path)
                    
                return img_str, formatted_detections
        # 遍历完所有帧都没有检测到目标
        cap.release()
        if not detected:
            print(f"视频共 {frame_count} 帧，未检测到任何目标")
            # 删除临时文件
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
            return None, "未检测到目标"
        
    except Exception as e:
        # 清理临时文件
        temp_video_path = os.path.join(settings.MEDIA_ROOT, 'temp_video.mp4')
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        import traceback
        error_details = traceback.format_exc()
        print(f"视频检测过程中出错: {error_details}")
        return None, f"检测过程中出错: {str(e)}"
