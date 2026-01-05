from rest_framework.response import Response 
from rest_framework import status
from rest_framework import serializers
from rest_framework.decorators import api_view , throttle_classes
from rest_framework.throttling import AnonRateThrottle
from ..serializers.doc_serializer import docserializer
from ..parsers.xer import xer_parser
import logging
from  django.conf import settings
import os
from django.core.cache import cache
from celery import shared_task
from ..data_extract.xer.table import construct_table
from rest_framework.parsers import MultiPartParser, FormParser
import hashlib
import time
import json
import tiktoken
import secrets
import string
from django.core.cache import cache
from dataclasses import dataclass
from enum import Enum

encoding = tiktoken.get_encoding("cl100k_base")

class status_enum(Enum):
    PROCESSING_TASKS = "processing_tasks"
    SUMMARIZING_PROJECT = "summarizing_project"
    COMPLETED = "completed"

@dataclass
class risk_forecast_status:
    max_tasks : int
    key: str
    processed_tasks : int = 0
    num_task_errors : int =0
    num_summary_errors : int =0
    status: str = status_enum.PROCESSING_TASKS.value
    latest_analysis : str | None = None

    def to_dict(self):
        return {
            "max_tasks": self.max_tasks,
            "key": self.key,
            "processed_tasks": self.processed_tasks,
            "latest_analysis": self.latest_analysis,
            "num_task_errors": self.num_task_errors,
            "num_summary_errors": self.num_summary_errors,
            "status": self.status
            }

@shared_task(queue =  "risk_queue" , rate_limit='10/m')
def risk_task(file_path: str , cache_key:str , check_if_processing_key:str):
        from app.services.risk_forecast import risk_service
        start_time = time.time()
        xer_doc = xer_parser(file_path)  #List
        structured_doc =  construct_table(xer_doc)
        tasks_list, tasks_grouped = structured_doc.unified() # list of unified table per task, grouped by wbs_id
        if os.path.exists(file_path):
           os.remove(file_path)
        if not tasks_list:
            return "No tasks found in the provided xer file."
        
        logging.warning(f"starting risk forecast analysis for {len(tasks_list)} tasks")

        risk_status  =   risk_forecast_status(max_tasks = len(tasks_list), key= check_if_processing_key)
        
        states =  [{"messages" :  json.dumps(task), "task_id": task.get("task_id"), "mode": "task" , "status": risk_status} for task in tasks_list]
        cache.set(check_if_processing_key , risk_status.to_dict() , timeout=60*60*10)  # cache for 10 hrs
        results  = risk_service(states)
        mapped_results =  list(map(lambda x: {"task_id": x.get("task_id"),
                                              "analysis": x.get("messages")[-1].content,
                                              "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False
                                              }, results))
        
        risk_status = cache.get(check_if_processing_key)
        risk_status =  risk_forecast_status(**risk_status)
        if risk_status.num_task_errors == risk_status.max_tasks:
            cache.set(check_if_processing_key , None , timeout=2)
            return "error: Failed to generate analysis at this time."
        #->> after all wbs analysis ->> summarize project delay analysis

        risk_status.status = status_enum.SUMMARIZING_PROJECT.value
        cache.set(check_if_processing_key , risk_status.to_dict() , timeout=60*60*10)  # cache for 10 hrs
        if len(encoding.encode(json.dumps(mapped_results))) <= 100000:
            summary_state =  {"messages" : json.dumps(mapped_results) , "mode": "summary" , "status": risk_status}

        else:
            half_task_results =  len(mapped_results) // 4
            tasks_results =  [mapped_results[:half_task_results]  , mapped_results[half_task_results: 2*half_task_results] ,
                              mapped_results[2*half_task_results: 3*half_task_results] , mapped_results[3*half_task_results: ] ]
            chunk_summary_state =  [{"messages" : json.dumps(results) , "mode": "summary" , "status": risk_status} for results in tasks_results]
            chunk_summary = risk_service(chunk_summary_state)
            mapped_chunk_results =  list(map(lambda x: {"analysis": x.get("messages")[-1].content,
                                              "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False}, chunk_summary ))
       
            summary_state =  {"messages" : json.dumps(mapped_chunk_results), "mode": "summary", "status": risk_status}
        
        final_summary =  risk_service([summary_state])[0] #pass summary_state to llm and get overall project delay analysis 
        risk_status = cache.get(check_if_processing_key)
        risk_status =  risk_forecast_status(**risk_status)
        risk_status.status = status_enum.COMPLETED.value
        cache.set(check_if_processing_key , risk_status.to_dict() , timeout=60*60*10)  # cache for 10 hrs
        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60 , 2)  #in mins
        logging.warning(f"analysis completed [risk analysis] , analysis took {elapsed_time} mins")
        if not hasattr(final_summary.get("messages")[-1] , "error"):
           cache.set(cache_key, risk_status.to_dict(), timeout=60*60*10)  # cache for 5 hrs
        else:
            cache.set(check_if_processing_key , None , timeout=2)
        return final_summary.get("messages")[-1].content

def file_hash(file_obj):
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


def cache_key(file_hash , task_name):
    return f"{task_name}_{file_hash}"
    

def gen_rand():
    return ''.join(secrets.choice(string.digits) for _ in range(10))


@api_view(['POST'])
def risk_forecast_controller(request):
    """Analyzes xer files for potential risks and recovery options"""
    parser_classes = [MultiPartParser , FormParser]
    file = request.FILES.get("file")

    if file and file.name.endswith(('.xer')):  
        filehash =  file_hash(file)
        key = cache_key(filehash , "risk_forecast")
        check_if_processing_key = f"{key}:processing"
        cached_result = cache.get(key)
        if cached_result:
            logging.info("Returning cached result")
            return Response(cached_result, status=status.HTTP_200_OK)
        elif cache.get(check_if_processing_key):  ##check if the current file is processing
            return Response(cache.get(check_if_processing_key), status=status.HTTP_202_ACCEPTED)
        else:
            logging.info("No cached result found, processing file")
        
            tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)

            logging.warning(f"Processing file: {file.name}")
            file_path = os.path.join(tmp_dir, f"{gen_rand()}_{file.name}")
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            t =  risk_task.delay(file_path , key , check_if_processing_key)
            cache.set(check_if_processing_key , {'task_id': t.id, 'data_key': key , 'status': 'processing'} , timeout=60*60*3)
            return Response({'task_id': t.id, 'data_key': key , 'status': 'processing'}, status=status.HTTP_202_ACCEPTED)
   
    else:
        return Response({"error": "file not valid, only '.xer' file is allowed"}, status = status.HTTP_400_BAD_REQUEST)