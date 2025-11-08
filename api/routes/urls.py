from django.urls import path
from ..controllers import delay_analysis_controller  as delay
from ..controllers import risk_forecast_con as risk
from ..controllers import project_report_controller as p
from ..controllers import schedule_opt_controller as s
from ..controllers import drone_report_con as d
from ..controllers import task_status


urlpatterns =  [
    path("delay" , delay.delay_analysis_controller,  name = "delay" ) , 
    path("overall_report" , p.progress_report_controller , name = "overall_report"),
    path("risk_forecast" , risk.risk_forecast_controller , name = "risk_forecast"),
    path("schedule_opt" ,  s.schedule_opt_controller ,  name =  "schedule_opt"),
    path("video_analyzer" ,  d.drone_report_controller ,  name =  "video_analyzer"),
    path('status', task_status.status, name='task_status'),
    ]