from rest_framework.decorators import api_view
from rest_framework.response import Response
from celery.result import AsyncResult 
from django.core.cache import cache
from rest_framework import status as s
from langchain_core.messages import AIMessage


@api_view(['POST']) 
def status(request):
    """Used to retrieve tasks from celery worker"""
    task_id = request.data.get('task_id')
    if not task_id:
        return Response({'error': 'task_id is required'}, status=s.HTTP_400_BAD_REQUEST)
    data_key =  request.data.get('data_key')
    if not data_key:
        return Response({'error': 'data_key is required'}, status=s.HTTP_400_BAD_REQUEST)
    
    result = AsyncResult(task_id) 
    if result.ready():
        stored = cache.get(data_key)
        cache.set(f"{data_key.split("_")[-1]}:processing" , None , timeout=2)
        if stored:
            return Response(stored , status = s.HTTP_200_OK)
        else:
            return Response({"error": "Failed to generate analysis at this time or result unavailable"} , status = s.HTTP_201_CREATED)
    else:
        return Response({'status': result.status,'task_id': task_id , 'progress': cache.get(f"{data_key.split("_")[-1]}:processing" , {'processed_tasks': 0})}, status = s.HTTP_202_ACCEPTED)