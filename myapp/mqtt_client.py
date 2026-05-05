import paho.mqtt.client as mqtt
import json
from django.utils import timezone
from .models import MQTTMessage, Da
import threading
import time
import json

class MQTTClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self.broker_host = "120.27.235.176"  # 默认MQTT broker
        self.broker_port = 1883  # 标准MQTT端口，Android端可能作为客户端连接
        self.topics = ["dxj"]  # 默认订阅主题
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("成功连接到MQTT服务器")
            self.connected = True
            # 订阅所有主题
            for topic in self.topics:
                client.subscribe(topic)
                print(f"已订阅主题: {topic}")
        else:
            print(f"连接失败，返回码: {rc}")
            
    def on_message(self, client, userdata, msg):
        try:
            print(f"收到消息: {msg.topic} -> {msg.payload.decode()}")
            
            # 保存消息到数据库
            mqtt_message = MQTTMessage(
                topic=msg.topic,
                payload=msg.payload.decode(),
                qos=msg.qos
            )
            mqtt_message.save()
            
            # 解析JSON数据并保存到Da表
            try:
                payload_data = json.loads(msg.payload.decode())
                
                # 检查是否包含传感器数据
                if isinstance(payload_data, dict):
                    # 获取当前时间戳
                    current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 创建Da记录
                    da_record = Da(
                        temp=payload_data.get('dht11_temper', 0.0),
                        light=payload_data.get('light', 0.0),
                        do=payload_data.get('O2', 0.0),
                        tds=payload_data.get('TDS', 0.0),
                        time=current_time
                    )
                    da_record.save()
                    print(f"数据已保存到datas表: {da_record}")
                    
            except (json.JSONDecodeError, ValueError) as json_error:
                print(f"JSON解析失败: {json_error}")
            except Exception as save_error:
                print(f"保存到datas表失败: {save_error}")
            
        except Exception as e:
            print(f"处理消息时出错: {e}")
            
    def on_disconnect(self, client, userdata, rc):
        print("与MQTT服务器断开连接")
        self.connected = False
        
    def connect(self, host=None, port=None, topics=None):
        if host:
            self.broker_host = host
        if port:
            self.broker_port = port
        if topics:
            self.topics = topics
            
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        try:
            # 设置连接超时时间为10秒
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            print(f"正在连接到 {self.broker_host}:{self.broker_port}，超时时间: 10秒")
            
            # 启动网络循环
            self.client.loop_start()
            
            # 等待连接建立，最多等待5秒
            import time
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.connected:
                    print("MQTT连接成功建立")
                    return True
                time.sleep(0.1)
            
            # 如果5秒后仍未连接，检查连接状态
            if not self.connected:
                print("MQTT连接超时，可能broker未运行或网络不可达")
                # 停止网络循环
                self.client.loop_stop()
                return False
                
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
            
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            
    def publish(self, topic, message, qos=0):
        if self.connected and self.client:
            result = self.client.publish(topic, message, qos=qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"消息已发送: {topic} -> {message}")
                return True
            else:
                print(f"发送失败: {result.rc}")
                return False
        else:
            print("MQTT客户端未连接")
            return False
            
    def is_connected(self):
        return self.connected

# 全局MQTT客户端实例
mqtt_client = MQTTClient()

def start_mqtt_client(host=None, port=None, topics=None):
    """启动MQTT客户端"""
    if not mqtt_client.is_connected():
        return mqtt_client.connect(host, port, topics)
    return True

def stop_mqtt_client():
    """停止MQTT客户端"""
    mqtt_client.disconnect()

def send_message(topic, message):
    """发送MQTT消息"""
    return mqtt_client.publish(topic, message)

def get_messages():
    """获取所有MQTT消息"""
    return MQTTMessage.objects.all()
