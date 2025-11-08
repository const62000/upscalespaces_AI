import os
from celery import Celery
from kombu import Exchange , Queue


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'upscale.settings')
app = Celery('upscale')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue("delay_queue" , Exchange("delay_queue") ,routing_key= "delay_queue"),
     Queue("report_queue" , Exchange("report_queue") ,routing_key= "report_queue"),
      Queue("risk_queue" , Exchange("risk_queue") ,routing_key= "risk_queue"),
      Queue("sch_queue" , Exchange("sch_queue") ,routing_key= "sch_queue"),
      Queue("drone_queue" , Exchange("drone_queue") ,routing_key= "drone_queue")
)
