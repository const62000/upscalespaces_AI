from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def index(_request):
    return Response(
        {
            "service": "UpscaleSpaces AI",
            "status": "ok",
            "routes": {
                "delay": "/delay",
                "overall_report": "/overall_report",
                "risk_forecast": "/risk_forecast",
                "schedule_opt": "/schedule_opt",
                "video_analyzer": "/video_analyzer",
                "task_status": "/status",
                "admin": "/admin/",
                "django_rq": "/django-rq/",
            },
            "message": "Upload .xer to endpoints as documented; see README.md.",
        }
    )