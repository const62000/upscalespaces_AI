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
from app.prompts.proj_report import prompt
from rest_framework.parsers import MultiPartParser, FormParser
import hashlib
import tiktoken
import json
import time
import secrets
import string
from django.core.cache import cache
from enum import Enum
from dataclasses import dataclass



encoding = tiktoken.get_encoding("cl100k_base")

class status_enum(Enum):
    PROCESSING_TASKS = "processing_tasks"
    SUMMARIZING_PROJECT = "summarizing_project"
    COMPLETED = "completed"

@dataclass
class project_report_status:
    max_tasks : int
    key: str
    processed_tasks: int = 0
    num_task_errors: int =0
    num_summary_errors: int =0
    num_dronereport_errors: int =0
    status: str = status_enum.PROCESSING_TASKS.value
    file_summary : str | None = None
    latest_analysis : str | None = None

    def to_dict(self):
        return {
            "max_tasks": self.max_tasks,
            "key": self.key,
            "processed_tasks": self.processed_tasks,
            "file_summary": self.file_summary,
            "latest_analysis": self.latest_analysis,
            "num_task_errors": self.num_task_errors,
            "num_summary_errors": self.num_summary_errors,
            "num_dronereport_errors": self.num_dronereport_errors,
            "status": self.status
            }
    
@shared_task(queue = "drone_queue" , rate_limit='10/m')  ##controls num of request, that can be made.. if it surpasses 5 it lines it up in queue
def drone_task(file_path: str , xer_key , cache_key , video_path: str, check_if_processing_key:str ):
        from app.services.project_report import project_report_service
        from app.services.video_analyzer import video_analyzer
        start_time = time.time()
        summary_without_video = cache.get(xer_key)
        
        if not summary_without_video:
            xer_doc = xer_parser(file_path)  #List
            structured_doc =  construct_table(xer_doc)
            tasks_list , tasks_grouped = structured_doc.unified() # list of unified table per task, filtered by wbs
           
            if os.path.exists(file_path):
               os.remove(file_path)
            if not tasks_list:
               return "No tasks found in the provided xer file."
            
            projectreportstatus =  project_report_status(max_tasks = len(tasks_list), key= check_if_processing_key)
            logging.warning(f"starting proj summary[ with video] for {len(tasks_list)} tasks")
            states =  [{"messages" :  json.dumps(task), "task_id": task.get("task_id"), "mode": "task" , "status": projectreportstatus , "task_type": None} for task in tasks_list]
            results =  project_report_service(states) 
            mapped_results =  list(map(lambda x: {"task_id": x.get("task_id"),
                                              "analysis": x.get("messages")[-1].content,
                                              "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False
                                              }, results))
            projectreportstatus  = cache.get(check_if_processing_key)
            projectreportstatus  =  project_report_status(**projectreportstatus)
            if projectreportstatus.num_task_errors == projectreportstatus.max_tasks:
                cache.set(check_if_processing_key , None , timeout=2)
                return "error: Failed to generate analysis at this time."
            
            projectreportstatus.status = status_enum.SUMMARIZING_PROJECT.value
            cache.set(check_if_processing_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 10 hrs
            
            if len(encoding.encode(json.dumps(mapped_results))) < 100000:
                logging.warning("generating project summary")
                summary_state =  {"messages" : json.dumps(mapped_results),  "mode": "summary_1" , "task_type": "proj_sum" ,  "status": projectreportstatus}

            else:
                half_task_results =  len(mapped_results) // 4
                tasks_results =  [mapped_results[:half_task_results]  , mapped_results[half_task_results: 2*half_task_results] ,
                                mapped_results[2*half_task_results: 3*half_task_results] , mapped_results[3*half_task_results: ] ]
                chunk_summary_state =  [{"messages" : json.dumps(results) , "mode": "summary_1" , "task_type": "proj_sum", "status": projectreportstatus } for results in tasks_results]
                chunk_summary = project_report_service(chunk_summary_state)
                mapped_chunk_results =  list(map(lambda x: {"analysis": x.get("messages")[-1].content,
                                                "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False}, chunk_summary ))
               
                summary_state =  {"messages" : json.dumps(mapped_chunk_results), "mode": "summary_1","task_type": "proj_sum", "status": projectreportstatus}
            

            final_summary =  project_report_service([summary_state])[0].get("messages")[-1] #pass summary_state to llm and get overall project delay analysis 
            logging.warning("analysis completed  (no video) [drone report]")
            if not hasattr(final_summary , "error"):
               final_summary = final_summary.content
               projectreportstatus = cache.get(check_if_processing_key)
               projectreportstatus =  project_report_status(**projectreportstatus)
               projectreportstatus.file_summary = final_summary
               cache.set(check_if_processing_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 10 hrs
               cache.set(xer_key ,  projectreportstatus.to_dict() , timeout=60*60*5)  #cache final summary w/o image summary
              
            else:
                cache.set(check_if_processing_key , None , timeout=2)
                return final_summary.content
        else:
            logging.warning("cached proj summary found **[w/o video]")
            final_summary =  summary_without_video

            final_summary["key"] = check_if_processing_key
            final_summary["status"] = status_enum.SUMMARIZING_PROJECT.value
            final_summary["num_dronereport_errors"] = 0
            final_summary["num_summary_errors"] = 0
            cache.set(check_if_processing_key ,final_summary, timeout=60*60*10)

        
        if video_path:
            logging.warning('found attached video, resummarizing with video context')
            summary_with_video =  cache.get(cache_key) 
            projectreportstatus = cache.get(check_if_processing_key)
            projectreportstatus =  project_report_status(**projectreportstatus)
            if not summary_with_video:
                final_summary =  video_analyzer([{"messages" : projectreportstatus.file_summary, 
                                                "system_msg": prompt().summary_2() , 
                                                "video_path" : video_path,
                                                "task_type": "proj_sum" , 
                                                "status" : projectreportstatus}])[0].get("messages")[-1]
                logging.warning("analysis completed  (with video) [drone report]")
                if os.path.exists(video_path):
                    os.remove(video_path)
                if not hasattr(final_summary , "error"):
                    cache.set(cache_key, final_summary.content, timeout=60*60*5)
                else:
                   cache.set(check_if_processing_key , None , timeout=2)
                final_summary = final_summary.content
            else:
                logging.warning("cached proj summary found **[with video]")
                if os.path.exists(video_path):
                    os.remove(video_path)
                final_summary =  summary_with_video
        projectreportstatus = cache.get(check_if_processing_key)
        if projectreportstatus:
            projectreportstatus =  project_report_status(**projectreportstatus)
            projectreportstatus.status = status_enum.COMPLETED.value
            cache.set(cache_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 10 hrs
        else:
            cache.set(cache_key , projectreportstatus , timeout=60*60*10)  # cache for 10 hrs

        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60 , 2)  #in mins
        logging.warning(f"analysis completed [drone_report] , analysis took {elapsed_time} mins")
        return final_summary
        
def file_hash(file_obj , video_objs = None):
    if video_objs:
       objs =  video_objs + [file_obj]
    else:
        objs =  [file_obj]

    hasher = hashlib.sha256()
    for f_obj in objs:
        for chunk in f_obj.chunks():
            hasher.update(chunk)
    return hasher.hexdigest()



def cache_key(file_hash , task_name):
    return f"{task_name}_{file_hash}"

def gen_rand():
    return ''.join(secrets.choice(string.digits) for _ in range(10))


    
@api_view(['POST'])
def drone_report_controller(request):
    """Reports general overview of the progress of the xer files, with or without site images """
    parser_classes = [MultiPartParser , FormParser]

    file = request.FILES.get("file")
    video = request.FILES.get("video")
    
    if not video or not file:
        return Response ({"error": "file and drone video in '.mp4','.mkv' ,'.avi' must be provided"} , status = status.HTTP_400_BAD_REQUEST)
    
    if file.name.endswith(('.xer')) and video.name.endswith(('.mp4','.mkv' ,'.avi')):
        filehash =  file_hash(file , [video])
        key = cache_key(filehash , "drone_report")
        check_if_processing_key = f"{key}:processing"

        xer_hash = file_hash(file)
        xer_key = cache_key(xer_hash, "project_report")

        cached_result = cache.get(key)
        if cached_result:
            logging.warning("Returning cached result")
            return Response(cached_result, status=status.HTTP_200_OK)
        elif cache.get(check_if_processing_key):  ##check if the current file is processing
            return Response(cache.get(check_if_processing_key), status=status.HTTP_202_ACCEPTED)
    
        else:
            logging.info("No cached file result found, processing file")
            tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)
            
            logging.warning(f"Processing xer file: {file.name}")
            file_path = os.path.join(tmp_dir, f"{gen_rand()}_{file.name}")
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            
            logging.warning(f"Processing video file: {video.name}")
            vidfile_path = os.path.join(tmp_dir, f"{gen_rand()}_{video.name}")
            with open(vidfile_path, 'wb+') as destination:
                for chunk in video.chunks():
                    destination.write(chunk)
            t  = drone_task.delay(file_path ,xer_key ,key , vidfile_path , check_if_processing_key)
            cache.set(check_if_processing_key , {'task_id': t.id, 'data_key': key , 'status': 'processing'} , timeout=60*60*3)
            return Response({'task_id': t.id, 'data_key': key , 'status': 'processing'}, status=status.HTTP_202_ACCEPTED)
    
    else:
        return Response({"error": "file not valid , only .xer file allowed and video in '.mp4','.mkv' ,'.avi' "}, status = status.HTTP_400_BAD_REQUEST)