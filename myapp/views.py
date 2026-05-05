from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from myapp.models import Us, MQTTMessage, Da
from myapp.mqtt_client import start_mqtt_client, stop_mqtt_client, send_message, get_messages, mqtt_client
from myapp.decorators import login_required
from myapp.yolov8_utils import load_yolov8_model, detect_image, detect_video
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import models
import os
import json
import base64
from django.db.models import Avg
from datetime import datetime, timedelta

# Create your views here.
@login_required
def index(request):
    username = request.session.get('username', '')
    context = {"username": username} 
    return render(request,'myapp/HPage.html', context)
    
# 登录视图
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            # 查询数据库验证用户
            user = Us.objects.get(name=username, password=password)
            # 登录成功，启动MQTT连接并订阅dxj主题
            if start_mqtt_client(topics=["dxj"]):
                print(f"用户 {username} 登录成功，MQTT已连接")
                # 存储用户信息到session
                request.session['user_id'] = user.id
                request.session['username'] = user.name
                # 重定向到index.html页面
                return redirect('index')
            else:
                print("MQTT连接失败")
                return redirect('/login')         
        except Us.DoesNotExist:
            # 用户不存在或密码错误
            print(f"登录失败: 用户名={username}, 密码={password}")
            return redirect('/login?error=1')
        except Exception as e:
            print(f"登录过程中出错: {e}")
            return redirect('/login?error=1')
    # GET请求显示登录页面
    return render(request, 'myapp/login.html')

#浏览用户信息
@login_required
def indexUsers(request):
    try:
        ulist = Us.objects.all()
        # 获取当前登录用户名
        username = request.session.get('username', '')
        context = {
            "uslist": ulist,
            "username": username
        }
        return render(request,"myapp/us/index.html",context)
    except Exception as e:
         context = {"info": f"失败: {str(e)}"}  # 捕获并显示错误信息
         return render(request,"myapp/us/info.html",context)
#加载添加用户信息表单
@login_required
def addUsers(request):
    username = request.session.get('username', '')
    context = {"username": username}
    return render(request,"myapp/us/add.html", context)
#执行用户信息添加
@login_required
def insetUsers(request):
    try:
        ob = Us()
        ob.id = request.POST['id']
        ob.name = request.POST['name']
        ob.password = request.POST['password']
        ob.save()
        username = request.session.get('username', '')
        context = {"info":"添加成功", "username": username}
    except Exception as e:
         username = request.session.get('username', '')
         context = {"info": f"添加失败: {str(e)}", "username": username}  # 捕获并显示错误信息
    return render(request,"myapp/us/info.html",context)
#执行用户信息删除
@login_required
def delUsers(request,uid=0):
    try:
        ob = Us.objects.get(id=uid)
        ob.delete()
        username = request.session.get('username', '')
        context = {"info":"删除成功", "username": username}
    except Exception as e:
         username = request.session.get('username', '')
         context = {"info": f"删除失败: {str(e)}", "username": username}  # 捕获并显示错误信息
    return render(request,"myapp/us/info.html",context)
#加载用户信息修改表单
@login_required
def editUsers(request,uid=0):
    try:
        ob = Us.objects.get(id=uid)
        username = request.session.get('username', '')
        context = {"ub": ob, "username": username}
        return render(request,"myapp/us/edit.html",context)
    except Exception as e:
        username = request.session.get('username', '')
        context = {"info": f"失败: {str(e)}", "username": username}  # 捕获并显示错误信息
        return render(request,"myapp/us/info.html",context)
#执行用户信息修改
@login_required
def updateUsers(request):
    try:
        uid = request.POST['id']
        ob = Us.objects.get(id=uid)
        ob.id = request.POST['id']
        ob.name = request.POST['name']
        ob.password = request.POST['password']
        ob.save()
        username = request.session.get('username', '')
        context = {"info":"成功", "username": username}
    except Exception as e:
         username = request.session.get('username', '')
         context = {"info": f"失败: {str(e)}", "username": username}  # 捕获并显示错误信息
    return render(request,"myapp/us/info.html",context)
# 登出视图
def logout(request):
    """用户登出"""
    # 清除session中的用户信息
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'username' in request.session:
        del request.session['username']
    # 停止MQTT连接
    stop_mqtt_client()
    # 重定向到登录页面
    return redirect('login')




# MQTT相关视图
@login_required
def mqtt_dashboard(request):
    context = {
        'connected': mqtt_client.is_connected(),
        'broker_host': mqtt_client.broker_host,
        'broker_port': mqtt_client.broker_port,
        'topics': mqtt_client.topics,
    }
    return render(request, "myapp/mqtt/dashboard.html", context)

@login_required
def mqtt_connect_confirm(request):
    """MQTT连接确认页面"""
    if request.method == 'POST':
        # 保存连接参数到session，用于确认后使用
        request.session['mqtt_host'] = request.POST.get('host', mqtt_client.broker_host)
        request.session['mqtt_port'] = request.POST.get('port', mqtt_client.broker_port)
        request.session['mqtt_topics'] = request.POST.get('topics', '')
        
        username = request.session.get('username', '')
        context = {
            'host': request.session['mqtt_host'],
            'port': request.session['mqtt_port'],
            'topics': request.session['mqtt_topics'],
            'connected': mqtt_client.is_connected(),
            'username': username
        }
        return render(request, "myapp/mqtt/confirm_connect.html", context)
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

def mqtt_connect(request):
    """执行MQTT连接"""
    if request.method == 'POST':
        try:
            # 从session获取连接参数
            host = request.session.get('mqtt_host', mqtt_client.broker_host)
            port = int(request.session.get('mqtt_port', mqtt_client.broker_port))
            topics = request.session.get('mqtt_topics', '').split(',')
            topics = [topic.strip() for topic in topics if topic.strip()]
            
            # 清除session中的连接参数
            if 'mqtt_host' in request.session:
                del request.session['mqtt_host']
            if 'mqtt_port' in request.session:
                del request.session['mqtt_port']
            if 'mqtt_topics' in request.session:
                del request.session['mqtt_topics']
            
            username = request.session.get('username', '')
            if start_mqtt_client(host, port, topics):
                return render(request, "myapp/mqtt/info.html", {"info": "连接成功", "username": username})
            else:
                return render(request, "myapp/mqtt/info.html", {"info": "连接失败", "username": username})
        except Exception as e:
            username = request.session.get('username', '')
            return render(request, "myapp/mqtt/info.html", {"info": f"连接错误: {str(e)}", "username": username})
    
    username = request.session.get('username', '')
    return render(request, "myapp/mqtt/info.html", {"info": "无效的请求方法", "username": username})

def mqtt_disconnect(request):
    """断开MQTT连接"""
    stop_mqtt_client()
    return redirect('mqtt_dashboard')


def mqtt_send_message(request):
    """发送MQTT消息"""
    if request.method == 'POST':
        try:
            topic = request.POST.get('topic', 'test/topic')
            message = request.POST.get('message', '')
            
            if send_message(topic, message):
                return redirect('mqtt_dashboard')
            else:
                return redirect('mqtt_dashboard')
        except Exception as e:
            return redirect('mqtt_dashboard')
    return redirect('mqtt_dashboard')

@login_required
def mqtt_get_messages(request):
    """获取MQTT消息列表并在datas_view.html中显示"""
    # 获取所有消息并按时间顺序排序（最新的在前面）
    all_messages = MQTTMessage.objects.all().order_by('-timestamp')
    
    # 处理消息数据，解析JSON格式
    processed_messages = []
    for message in all_messages:
        try:
            # 确保payload是字符串
            payload_str = str(message.payload)      
            # 尝试解析JSON数据
            payload_data = json.loads(payload_str)
            # 确保payload_data是字典类型
            if isinstance(payload_data, dict):
                # 提取传感器数据
                sensor_data = {
                    'timestamp': message.timestamp,
                    'topic': message.topic,
                    'temperature': payload_data.get('dht11_temper'),
                    'light': payload_data.get('light'),
                    'oxygen': payload_data.get('O2'),
                    'tds': payload_data.get('TDS'),
                    'warn': payload_data.get('warn'),
                    'qos': message.qos,
                    'raw_payload': message.payload  # 保留原始数据
                }
                processed_messages.append(sensor_data)
            else:
                # 如果不是字典，保持原样
                processed_messages.append({
                    'timestamp': message.timestamp,
                    'topic': message.topic,
                    'temperature': None,
                    'light': None,
                    'oxygen': None,
                    'tds': None,
                    'warn': None,
                    'qos': message.qos,
                    'raw_payload': message.payload
                }) 
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # 如果不是JSON格式，保持原样
            processed_messages.append({
                'timestamp': message.timestamp,
                'topic': message.topic,
                'temperature': None,
                'light': None,
                'oxygen': None,
                'tds': None,
                'warn': None,
                'qos': message.qos,
                'raw_payload': message.payload
            })
    # 分页处理，每页10条数据
    paginator = Paginator(processed_messages, 10)
    page_number = request.GET.get('page')  
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    username = request.session.get('username', '')
    context = {
        'messages': page_obj,  # 使用分页对象
        'page_obj': page_obj,  # 分页对象，用于模板中的分页控件
        'connected': mqtt_client.is_connected(),
        'broker_host': mqtt_client.broker_host,
        'broker_port': mqtt_client.broker_port,
        'topics': mqtt_client.topics,
        'username': username
    }
    return render(request, "myapp/data_s/datas_view.html", context)

def mqtt_clear_messages(request):
    """清空MQTT消息"""
    if request.method == 'POST':
        try:
            MQTTMessage.objects.all().delete()
        except Exception as e:
            pass
    return redirect('mqtt_dashboard')




# 折线图数据视图
@login_required
def line_chart_view(request):
    username = request.session.get('username', '')
    
    # 获取日期参数，默认为最近10天
    end_date_str = request.GET.get('end_date', '')
    start_date_str = request.GET.get('start_date', '')
    
    # 设置默认日期范围
    end_date = datetime.now().date()
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = datetime.now().date()
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date - timedelta(days=9)
    else:
        start_date = end_date - timedelta(days=9)
    
    # 确保开始日期不晚于结束日期
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # 确保日期范围不超过10天
    date_range = (end_date - start_date).days + 1
    if date_range > 10:
        start_date = end_date - timedelta(days=9)
    
    # 生成日期列表
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)
    
    # 初始化数据数组
    date_labels = []
    temp_data = []
    light_data = []
    oxygen_data = []
    tds_data = []
    
    # 对每个日期计算平均值
    for date in date_list:
        # 格式化日期标签为"X月X日"格式
        date_label = f"{date.month}月{date.day}日"
        date_labels.append(date_label)
        
        # 计算日期时间范围
        start_datetime = datetime.combine(date, datetime.min.time())
        end_datetime = datetime.combine(date + timedelta(days=1), datetime.min.time())
        
        # 查询该日期的MQTTMessage数据
        messages = MQTTMessage.objects.filter(
            timestamp__gte=start_datetime,
            timestamp__lt=end_datetime
        )
        
        # 初始化统计变量
        temp_sum = 0
        light_sum = 0
        oxygen_sum = 0
        tds_sum = 0
        count = 0
        
        # 处理每条消息，解析payload
        for message in messages:
            try:
                # 解析JSON payload
                payload_str = str(message.payload)
                payload_data = json.loads(payload_str)
                
                if isinstance(payload_data, dict):
                    # 提取传感器数据
                    temp_val = payload_data.get('dht11_temper')
                    light_val = payload_data.get('light')
                    oxygen_val = payload_data.get('O2')
                    tds_val = payload_data.get('TDS')
                    
                    # 累加有效数据
                    if temp_val is not None:
                        temp_sum += float(temp_val)
                        count += 1
                    if light_val is not None:
                        light_sum += float(light_val)
                    if oxygen_val is not None:
                        oxygen_sum += float(oxygen_val)
                    if tds_val is not None:
                        tds_sum += float(tds_val)
                        
            except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
                # 跳过无法解析的消息
                continue
        
        # 计算平均值
        if count > 0:
            temp_avg = round(temp_sum / count, 2) if temp_sum > 0 else 0
            light_avg = round(light_sum / count, 2) if light_sum > 0 else 0
            oxygen_avg = round(oxygen_sum / count, 2) if oxygen_sum > 0 else 0
            tds_avg = round(tds_sum / count, 2) if tds_sum > 0 else 0
        else:
            temp_avg = 0
            light_avg = 0
            oxygen_avg = 0
            tds_avg = 0
        
        # 添加到数据数组
        temp_data.append(temp_avg)
        light_data.append(light_avg/10)
        oxygen_data.append(oxygen_avg)
        tds_data.append(tds_avg/10)
    
    # 准备ECharts数据
    chart_data = {
        'dates': date_labels,
        'temp': temp_data,
        'light': light_data,
        'oxygen': oxygen_data,
        'tds': tds_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    context = {
        'username': username,
        'chart_data_json': json.dumps(chart_data),
        'chart_data': chart_data,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'connected': mqtt_client.is_connected()
    }
    
    return render(request, "myapp/data_s/line_chart.html", context)




# 阈值设置相关视图
@login_required
def threshold_settings(request):
    """阈值设置界面"""
    username = request.session.get('username', '')
    context = {
        'username': username,
        'connected': mqtt_client.is_connected()
    }
    return render(request, "myapp/threshold/settings.html", context)


@login_required
def set_threshold(request):
    """设置阈值并发送MQTT消息"""
    if request.method == 'POST':
        try:
            threshold_type = request.POST.get('type')
            min_value = request.POST.get('min')
            max_value = request.POST.get('max')
            
            # 验证参数
            if not all([threshold_type, min_value, max_value]):
                from django.contrib import messages
                messages.error(request, '请填写最小值和最大值')
                return redirect('threshold_settings')
            
            # 验证数值有效性
            try:
                min_float = float(min_value)
                max_float = float(max_value)
            except ValueError:
                from django.contrib import messages
                messages.error(request, '请输入有效的数字')
                return redirect('threshold_settings')
            
            # 验证最小值小于最大值
            if min_float >= max_float:
                from django.contrib import messages
                messages.error(request, '最小值必须小于最大值')
                return redirect('threshold_settings')
            
            # 根据类型构建MQTT消息
            if threshold_type == 'temperature':
                message = f"ti:{min_value},ta:{max_value}"
                topic = "dxj1"
            elif threshold_type == 'light':
                message = f"li:{min_value},la:{max_value}"  
                topic = "dxj1"
            elif threshold_type == 'oxygen':
                message = f"ti:{min_value},ta:{max_value}"  
                topic = "dxj1"
            elif threshold_type == 'tds':
                message = f"ti:{min_value},ta:{max_value}"  
                topic = "dxj1"
            else:
                from django.contrib import messages
                messages.error(request, '无效的阈值类型')
                return redirect('threshold_settings')
            
            # 发送MQTT消息
            if send_message(topic, message):
                from django.contrib import messages
                messages.success(request, f'{threshold_type}阈值设置成功: {message}')
                return redirect('threshold_settings')
            else:
                from django.contrib import messages
                messages.error(request, 'MQTT消息发送失败')
                return redirect('threshold_settings')
                
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'设置阈值时出错: {str(e)}')
            return redirect('threshold_settings')
    
    from django.contrib import messages
    messages.error(request, '无效的请求方法')
    return redirect('threshold_settings')

# YOLOv8目标检测视图
@login_required
def yolov8_detection(request):
    """YOLOv8目标检测界面"""
    username = request.session.get('username', '')
    context = {
        'username': username,
        'detection_result': None,
        'detection_info': None,
        'error_message': None
    }
    return render(request, "myapp/yolov8/detection.html", context)

@login_required
def yolov8_detect_image(request):
    """处理图片检测请求"""
    if request.method == 'POST' and request.FILES.get('image'):
        username = request.session.get('username', '')
        model = load_yolov8_model()
        
        if model is None:
            context = {
                'username': username,
                'error_message': 'YOLOv8模型加载失败'
            }
            return render(request, "myapp/yolov8/detection.html", context)
        
        image_file = request.FILES['image']
        result_image, detections = detect_image(image_file, model)
        
        if result_image is None:
            context = {
                'username': username,
                'error_message': detections  # 这里detections是错误信息
            }
            return render(request, "myapp/yolov8/detection.html", context)
        
        # 将图片转换为base64
        image_base64 = base64.b64encode(result_image).decode()
        
        # 确保base64字符串长度是4的倍数（添加必要的填充）
        padding = 4 - (len(image_base64) % 4)
        if padding != 4:  # 如果不是4的倍数
            image_base64 += '=' * padding
        
        context = {
            'username': username,
            'detection_result': image_base64,
            'detection_info': detections,
            'file_type': 'image'
        }
        return render(request, "myapp/yolov8/detection.html", context)
    
    return redirect('yolov8_detection')

@login_required
def yolov8_detect_video(request):
    """处理视频检测请求"""
    if request.method == 'POST' and request.FILES.get('video'):
        username = request.session.get('username', '')
        model = load_yolov8_model()
        
        if model is None:
            context = {
                'username': username,
                'error_message': 'YOLOv8模型加载失败'
            }
            return render(request, "myapp/yolov8/detection.html", context)
        
        video_file = request.FILES['video']
        result_image, detections = detect_video(video_file, model)
        
        if result_image is None:
            context = {
                'username': username,
                'error_message': detections  # 这里detections是错误信息
            }
            return render(request, "myapp/yolov8/detection.html", context)
        
        # 将图片转换为base64
        image_base64 = base64.b64encode(result_image).decode('utf-8')
        
        # 确保base64字符串长度是4的倍数（添加必要的填充）
        padding = 4 - (len(image_base64) % 4)
        if padding != 4:  # 如果不是4的倍数
            image_base64 += '=' * padding
        
        context = {
            'username': username,
            'detection_result': image_base64,
            'detection_info': detections,
            'file_type': 'video'
        }
        return render(request, "myapp/yolov8/detection.html", context)
    
    return redirect('yolov8_detection')

@login_required
def yolov8_realtime_detect(request):
    """实时摄像头检测 - 处理单帧图像检测"""
    if request.method == 'POST' and request.FILES.get('frame'):
        try:
            model = load_yolov8_model()
            if model is None:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'YOLOv8模型加载失败'
                })
            
            frame_file = request.FILES['frame']
            result_image, detections = detect_image(frame_file, model)
            
            if result_image is None:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'检测失败: {detections}'
                })
            
            # 将检测结果转换为base64
            image_base64 = base64.b64encode(result_image).decode('utf-8')
            
            # 确保base64字符串长度是4的倍数（添加必要的填充）
            # base64字符串长度必须是4的倍数，否则解码会失败
            padding = 4 - (len(image_base64) % 4)
            if padding != 4:  # 如果不是4的倍数
                image_base64 += '=' * padding
            
            return JsonResponse({
                'status': 'success',
                'detection_result': image_base64,
                'detection_info': detections,
                'detection_count': len(detections)
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"实时检测出错: {error_details}")
            return JsonResponse({
                'status': 'error', 
                'message': f'实时检测出错: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': '无效的请求或缺少帧数据'
    })
