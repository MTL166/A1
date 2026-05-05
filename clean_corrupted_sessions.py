"""
清理损坏的Django会话
"""
import os
import sys
import base64


def clean_corrupted_sessions():
    """清理损坏的会话"""
    # 设置Django环境
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myweb.settings')
    
    import django
    django.setup()
    
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    
    print("开始清理损坏的会话...")
    
    # 获取所有活跃会话
    sessions = Session.objects.filter(expire_date__gt=timezone.now())
    print(f"找到 {len(sessions)} 个活跃会话")
    
    corrupted_count = 0
    for session in sessions:
        try:
            # 尝试解码会话数据
            session_data = session.get_decoded()
            print(f"会话 {session.session_key[:10]}...: 解码成功")
        except Exception as e:
            error_str = str(e).lower()
            if 'base64' in error_str or 'binascii' in error_str:
                print(f"会话 {session.session_key[:10]}...: 损坏 - {e}")
                # 删除损坏的会话
                session.delete()
                corrupted_count += 1
                print(f"  已删除损坏的会话")
    
    print(f"\n清理完成。删除了 {corrupted_count} 个损坏的会话。")
    
    # 如果删除了会话，建议重启Django服务器
    if corrupted_count > 0:
        print("\n建议: 重启Django服务器以确保更改生效。")

if __name__ == "__main__":
    clean_corrupted_sessions()
