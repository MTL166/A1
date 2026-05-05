"""
自定义中间件：处理base64解码错误
"""
import base64
import traceback
from django.http import HttpResponse

class Base64ErrorMiddleware:
    """处理base64解码错误的中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 首先检查会话数据是否可解码
        if hasattr(request, 'session'):
            try:
                # 尝试访问会话数据，这会触发解码
                # 如果会话数据损坏，这里会抛出异常
                _ = request.session.keys()
            except Exception as e:
                error_str = str(e).lower()
                if 'base64' in error_str or 'binascii' in error_str or 'b64decode' in error_str:
                    print(f"Base64ErrorMiddleware: 检测到损坏的会话数据: {e}")
                    # 创建一个新的空会话
                    request.session.flush()
                    print("Base64ErrorMiddleware: 已清除损坏的会话数据")
        
        try:
            # 在处理请求之前，检查并清理可能的base64数据
            self._clean_request_data(request)
            
            response = self.get_response(request)
            return response
            
        except Exception as e:
            # 检查是否是base64错误
            error_str = str(e).lower()
            if 'base64' in error_str or 'binascii' in error_str or 'b64decode' in error_str:
                print(f"Base64ErrorMiddleware捕获到base64错误: {e}")
                print(f"错误类型: {type(e).__name__}")
                print(f"错误堆栈:\n{traceback.format_exc()}")
                
                # 尝试清理会话数据
                self._clean_session_data(request)
                
                # 对于根路径，返回一个简单的重定向或错误页面
                if request.path == '/':
                    # 重定向到登录页面或返回简单响应
                    from django.shortcuts import redirect
                    return redirect('login')
                
                # 对于其他路径，返回错误响应
                return HttpResponse(f"Base64解码错误: {e}", status=500)
            
            # 重新抛出其他异常
            raise
    
    def _clean_request_data(self, request):
        """清理请求中的base64数据"""
        # 安全地检查会话数据
        if hasattr(request, 'session'):
            try:
                for key in list(request.session.keys()):
                    value = request.session.get(key)
                    if isinstance(value, str) and len(value) == 89:
                        print(f"Base64ErrorMiddleware: 发现长度为89的会话数据: {key}")
                        try:
                            base64.b64decode(value)
                        except:
                            print(f"Base64ErrorMiddleware: 删除无效的base64会话数据: {key}")
                            del request.session[key]
            except Exception as e:
                print(f"Base64ErrorMiddleware: 清理会话数据时出错: {e}")
    
    def _clean_session_data(self, request):
        """清理会话数据"""
        if not hasattr(request, 'session'):
            return
            
        keys_to_delete = []
        try:
            for key in list(request.session.keys()):
                if any(base64_key in key.lower() for base64_key in 
                       ['base64', 'image', 'data', 'result', 'detection', 'token', 'csrf']):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                print(f"Base64ErrorMiddleware: 删除可能包含base64数据的会话键: {key}")
                del request.session[key]
            
            if keys_to_delete:
                request.session.save()
        except Exception as e:
            print(f"Base64ErrorMiddleware: 清理会话数据时出错: {e}")
