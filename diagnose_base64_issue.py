"""
诊断base64错误突然出现的原因
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myweb.settings')
django.setup()

from django.contrib.sessions.models import Session
from django.utils import timezone
from myapp.models import MQTTMessage
import base64
import json

def check_sessions_for_base64():
    """检查会话中是否有base64数据"""
    print("=== 检查会话数据 ===")
    
    # 获取所有活跃会话
    sessions = Session.objects.filter(expire_date__gt=timezone.now())
    print(f"找到 {len(sessions)} 个活跃会话")
    
    for i, session in enumerate(sessions[:5]):  # 只检查前5个会话
        try:
            session_data = session.get_decoded()
            if session_data:
                print(f"\n会话 {i+1}:")
                for key, value in session_data.items():
                    if isinstance(value, str):
                        if len(value) == 89:
                            print(f"  发现长度为89的字符串: {key}")
                            try:
                                base64.b64decode(value)
                                print(f"    ✓ 是有效的base64")
                            except:
                                print(f"    ✗ 不是有效的base64")
                        elif len(value) > 50:  # 检查较长的字符串
                            # 检查是否是base64格式的字符串
                            if all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in value):
                                print(f"  发现可能是base64的字符串: {key} (长度: {len(value)})")
        except Exception as e:
            print(f"解码会话时出错: {e}")
    
    print("\n" + "="*60 + "\n")

def check_mqtt_messages():
    """检查MQTT消息中是否有base64数据"""
    print("=== 检查MQTT消息 ===")
    
    messages = MQTTMessage.objects.all().order_by('-timestamp')[:10]
    print(f"检查最近 {len(messages)} 条MQTT消息")
    
    for i, message in enumerate(messages):
        try:
            payload = str(message.payload)
            if len(payload) == 89:
                print(f"\n消息 {i+1} (时间: {message.timestamp}, 主题: {message.topic}):")
                print(f"  发现长度为89的payload")
                try:
                    # 尝试解析为JSON
                    data = json.loads(payload)
                    print(f"    ✓ 是有效的JSON")
                    # 检查JSON中是否有base64数据
                    for key, value in data.items():
                        if isinstance(value, str) and len(value) == 89:
                            print(f"    JSON字段 '{key}' 长度为89")
                except json.JSONDecodeError:
                    print(f"    ✗ 不是有效的JSON")
                    try:
                        base64.b64decode(payload)
                        print(f"    ✓ 是有效的base64")
                    except:
                        print(f"    ✗ 不是有效的base64")
        except Exception as e:
            print(f"检查消息时出错: {e}")
    
    print("\n" + "="*60 + "\n")

def check_environment():
    """检查环境因素"""
    print("=== 检查环境 ===")
    
    print(f"Python版本: {sys.version}")
    print(f"Django版本: {django.get_version()}")
    
    # 检查base64模块
    try:
        import base64
        print(f"base64模块可用")
        
        # 测试base64编码/解码
        test_data = b"test data"
        encoded = base64.b64encode(test_data).decode('utf-8')
        decoded = base64.b64decode(encoded)
        print(f"base64测试: 编码 '{test_data}' -> '{encoded}' -> 解码成功")
    except Exception as e:
        print(f"base64模块测试失败: {e}")
    
    print("\n" + "="*60 + "\n")

def suggest_possible_causes():
    """提供可能的原因和建议"""
    print("=== 可能的原因和建议 ===")
    
    print("""
1. **会话数据损坏**:
   - 用户之前使用过YOLOv8检测功能，在浏览器缓存或会话中留下了base64数据
   - 解决方案: 清除浏览器缓存和cookie，或使用无痕模式访问

2. **浏览器缓存问题**:
   - 浏览器缓存了包含base64数据的页面
   - 解决方案: 强制刷新页面(Ctrl+F5)或清除缓存

3. **CSRF令牌问题**:
   - Django的CSRF令牌有时是base64编码的，可能被损坏
   - 解决方案: 中间件已经处理了这个问题

4. **并发访问问题**:
   - 多个用户同时访问可能导致会话数据混乱
   - 解决方案: 确保会话数据隔离

5. **数据存储问题**:
   - 数据库中的某些记录可能包含损坏的base64数据
   - 解决方案: 检查数据库中的异常数据

6. **外部数据源**:
   - 如果应用从外部API获取数据，可能收到了损坏的base64数据
   - 解决方案: 验证外部数据源的完整性

7. **字符编码问题**:
   - 数据传输过程中的编码问题可能导致base64字符串被截断
   - 解决方案: 确保使用正确的字符编码(UTF-8)

8. **网络传输问题**:
   - 网络不稳定可能导致数据包丢失，截断base64字符串
   - 解决方案: 实现数据完整性检查

建议的临时解决方案:
1. 清除浏览器缓存和cookie
2. 使用无痕模式访问网站
3. 重启Django服务器
4. 检查数据库中的异常数据
5. 查看Django日志获取更多错误信息
""")

if __name__ == "__main__":
    print("开始诊断base64错误问题...\n")
    
    try:
        check_environment()
        check_sessions_for_base64()
        check_mqtt_messages()
        suggest_possible_causes()
        
        print("\n诊断完成。请根据上述建议尝试解决问题。")
    except Exception as e:
        print(f"诊断过程中出错: {e}")
        import traceback
        traceback.print_exc()
