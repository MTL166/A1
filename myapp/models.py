from django.db import models
from datetime import datetime
# Create your models here.


class Us(models.Model):
    id =  models.IntegerField("ID")
    name = models.CharField("用户名",max_length=10,primary_key=True)
    password = models.IntegerField("密码")

    def __str__(self):
        return "%s:%d"%(self.id,self.name,self.password)
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息管理'

class Da(models.Model):
    id = models.AutoField("ID", primary_key=True)
    temp = models.FloatField("温度",max_length=6)
    light = models.FloatField("光照",max_length=6)
    do = models.FloatField("溶解氧",max_length=6)
    tds = models.FloatField("TDS",max_length=6)
    time = models.CharField("时间",max_length=20)

    def __str__(self):
        return "%s:%f:%f:%f:%f:%f"%(self.id,self.temp,self.light,self.do,self.tds,self.time)
    
    class Meta:
        db_table = 'datas'
        verbose_name = '数据信息'
        verbose_name_plural = '数据信息管理'


class MQTTMessage(models.Model):
    topic = models.CharField("主题", max_length=255)
    payload = models.TextField("消息内容")
    qos = models.IntegerField("服务质量", default=0)
    timestamp = models.DateTimeField("接收时间", auto_now_add=True)
    
    def __str__(self):
        return f"{self.topic}: {self.payload[:50]}"
    
    class Meta:
        db_table = 'mqtt_messages'
        verbose_name = 'MQTT消息'
        verbose_name_plural = 'MQTT消息管理'
        ordering = ['-timestamp']
