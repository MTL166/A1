from django.shortcuts import redirect
from functools import wraps

def login_required(view_func):
    """
    登录检查装饰器
    如果用户未登录，重定向到登录页面
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 检查session中是否有用户信息
        if 'user_id' not in request.session or 'username' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
