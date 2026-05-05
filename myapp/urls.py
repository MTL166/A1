from django.urls import path
from . import views

urlpatterns = [
    path('',views.index,name='index'),

    # 登录路由
    path('login', views.login, name='login'),
    # 登出路由
    path('logout', views.logout, name='logout'),

    path('users',views.indexUsers,name='indexusers'),
    path('users/add',views.addUsers,name='addusers'),
    path('users/insert',views.insetUsers,name='insertusers'),
    path('users/del/<int:uid>',views.delUsers,name='delusers'),
    path('users/edit/<int:uid>',views.editUsers,name='editusers'),
    path('users/update',views.updateUsers,name='updateusers'),
    
    # MQTT相关路由
    path('mqtt', views.mqtt_dashboard, name='mqtt_dashboard'),
    path('mqtt/connect/confirm', views.mqtt_connect_confirm, name='mqtt_connect_confirm'),
    path('mqtt/connect', views.mqtt_connect, name='mqtt_connect'),
    path('mqtt/disconnect', views.mqtt_disconnect, name='mqtt_disconnect'),
    path('mqtt/send', views.mqtt_send_message, name='mqtt_send'),
    #path('mqtt/messages', views.mqtt_get_messages, name='mqtt_get_messages'),
    path('mqtt/clear', views.mqtt_clear_messages, name='mqtt_clear'),
    
    # YOLOv8目标检测路由
    path('yolov8', views.yolov8_detection, name='yolov8_detection'),
    path('yolov8/detect/image', views.yolov8_detect_image, name='yolov8_detect_image'),
    path('yolov8/detect/video', views.yolov8_detect_video, name='yolov8_detect_video'),
    path('yolov8/realtime/detect', views.yolov8_realtime_detect, name='yolov8_realtime_detect'),
    
    # 阈值设置路由
    path('threshold', views.threshold_settings, name='threshold_settings'),
    path('threshold/set', views.set_threshold, name='set_threshold'),

    # 数据查看路由
    path('data_view_1',views.mqtt_get_messages,name='mqtt_get_messages'),
    
    # 折线图数据路由
    path('line_chart', views.line_chart_view, name='line_chart_view'),
]
