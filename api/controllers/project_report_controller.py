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
from app.prompts.proj_report import prompt
from rest_framework.parsers import MultiPartParser, FormParser
import hashlib
import tiktoken
import json
import time
import secrets
import string
from dataclasses import dataclass
from enum import Enum

encoding = tiktoken.get_encoding("cl100k_base")

class status_enum(Enum):
    PROCESSING_TASKS = "processing_tasks"
    SUMMARIZING_PROJECT = "summarizing_project"
    COMPLETED = "completed"

@dataclass
class project_report_status:
    max_tasks : int
    key: str
    processed_tasks : int = 0
    num_task_errors : int =0
    num_summary_errors : int =0
    num_dronereport_errors: int =0
    status: str = status_enum.PROCESSING_TASKS.value
    file_summary : str | None = None
    latest_analysis : str | None | dict = None

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
    
def save_tasks(other_tasks:list ,cache_key:str , xer_key:str , state: dict , report_dict: dict):
    xer_key =  xer_key.split("_")[-1]
    cache_key = cache_key.split("_")[-1]
    for task_type in other_tasks:
        out_dict  = report_dict
        if task_type == "delay_analysis":
            key =  f"delay_analysis_{xer_key}"
            out_dict["key"] = key
            out_dict["latest_analysis"] =  state.get("messages")[-1].delay_analysis if hasattr(state.get("messages")[-1] , "delay_analysis") else None
            out_dict["status"] = status_enum.COMPLETED.value
            if out_dict["latest_analysis"]:
                cache.set(key , out_dict, timeout=60*60*10)
        if task_type == "risk_forecast":
            key =  f"risk_forecast_{xer_key}"
            out_dict["key"] = key
            out_dict["latest_analysis"] =  state.get("messages")[-1].risk_forecast if hasattr(state.get("messages")[-1] , "risk_forecast") else None
            out_dict["status"] = status_enum.COMPLETED.value
            if out_dict["latest_analysis"]:
                cache.set(key , out_dict, timeout=60*60*10)
        if task_type == "sch_opt":
            key =  f"sch_opt_{xer_key}"
            out_dict["key"] = key
            out_dict["latest_analysis"] = state.get("messages")[-1].optimization_suggestions if hasattr(state.get("messages")[-1] , "optimization_suggestions") else None
            out_dict["status"] = status_enum.COMPLETED.value
            if out_dict["latest_analysis"]:
                cache.set(key , out_dict, timeout=60*60*10)
        if task_type ==  "project_report":
            key =  f"project_report_{xer_key}"
            out_dict["key"] = key
            out_dict["latest_analysis"] =  state.get("messages")[-1].overall_review  if hasattr(state.get("messages")[-1] , "overall_review") else None
            out_dict["status"] = status_enum.COMPLETED.value
            if out_dict["latest_analysis"]:
                cache.set(key , out_dict, timeout=60*60*10)
                key = f"project_report_{cache_key}"
                out_dict["key"] = key
                cache.set(key , out_dict, timeout=60*60*10)
@shared_task(queue = "report_queue" , rate_limit='10/m')  ##controls num of request, that can be made.. if it surpasses 5 it lines it up in queue
def report_task(file_path: str , xer_key , cache_key ,check_if_processing_key, saved_img_paths: list = None  ,  video_path: str = None):
        from app.services.project_report import project_report_service
        start_time = time.time()
        summary_without_img = cache.get(f"{xer_key}:tasks_summary")
        if not summary_without_img:
            xer_doc = xer_parser(file_path)  #List
            structured_doc =  construct_table(xer_doc)
            tasks_list , tasks_grouped = structured_doc.unified() # list of unified table per task, filtered by wbs
           
            if os.path.exists(file_path):
               os.remove(file_path)
            if not tasks_list:
               return "No tasks found in the provided xer file."
            
            projectreportstatus =  project_report_status(max_tasks = len(tasks_list), key= check_if_processing_key)
            logging.warning(f"starting project summary for {len(tasks_list)} tasks")
            states =  [{"messages" :  json.dumps(task), "task_id": task.get("task_id"), "mode": "default" , "status": projectreportstatus , "task_type": "task"} for task in tasks_list]
            results =  project_report_service(states) 
            mapped_results =  list(map(lambda x: {"task_id": x.get("task_id"),
                                              "analysis":{"delay_analysis" : x.get("messages")[-1].model_dump().get("delay_analysis"),
                                                          "risk_forecast": x.get("messages")[-1].model_dump().get("risk_forecast"),
                                                          "optimization_suggestions": x.get("messages")[-1].model_dump().get("optimization_suggestions"),
                                                          "overall_review": x.get("messages")[-1].model_dump().get("overall_review")
                                                          },
                                              "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False
                                              }, results))
            projectreportstatus  = cache.get(check_if_processing_key)
            projectreportstatus  =  project_report_status(**projectreportstatus)
            if projectreportstatus.num_task_errors == projectreportstatus.max_tasks:
                cache.set(check_if_processing_key , None , timeout=2)
                return "error: Failed to generate analysis at this time."
            
            projectreportstatus.status = status_enum.SUMMARIZING_PROJECT.value
            cache.set(check_if_processing_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 10 hrs
            cache.set(f"{xer_key}:tasks_summary" ,  mapped_results, timeout=60*60*10)  #cache task results w/o image summary
            

            if len(encoding.encode(json.dumps(mapped_results))) < 30000:
                logging.warning("generating project summary")
                summary_state =  {"messages" : json.dumps(mapped_results) + f"\n total_tasks : {len(mapped_results)}",  "mode": "default" , "task_type": "proj_sum" ,   "status": projectreportstatus}

            else:
                half_task_results =  len(mapped_results) // 4
                tasks_results =  [mapped_results[:half_task_results]  , mapped_results[half_task_results: 2*half_task_results] ,
                                mapped_results[2*half_task_results: 3*half_task_results] , mapped_results[3*half_task_results: ] ]
                chunk_summary_state =  [{"messages" : json.dumps(results)+ f"\n total_tasks : {len(results)}" , "mode": "default" , "task_type": "proj_sum", "status": projectreportstatus } for results in tasks_results]
                chunk_summary = project_report_service(chunk_summary_state)
                mapped_chunk_results =  list(map(lambda x: {"analysis": x.get("messages")[-1].content,
                                                "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False}, chunk_summary ))
               
                summary_state =  {"messages" : json.dumps(mapped_chunk_results) + f"\n total_tasks : {len(mapped_results)}", "mode": "default","task_type": "proj_sum", "status": projectreportstatus}
            
            if saved_img_paths:
                logging.warning('found attached imaged, resummarizing with image context')
                summary_state["img_paths"] = saved_img_paths
                summary_state["mode"] = "img"
            if video_path:
                logging.warning('found attached video, analyzing video for image context')
                summary_state["video_path"] = video_path
                summary_state["mode"] = "vid"

            final_summary =  project_report_service([summary_state])[0].get("messages")[-1] #pass summary_state to llm and get overall project delay analysis 
            logging.warning("analysis completed [project report]")
            if not hasattr(final_summary , "error"):
               final_summary = final_summary.content
               projectreportstatus = cache.get(check_if_processing_key)
               projectreportstatus =  project_report_status(**projectreportstatus)
               projectreportstatus.file_summary = final_summary

                        
               cache.set(check_if_processing_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 5 hrs
            else:
                cache.set(check_if_processing_key , None , timeout=2)
                return final_summary.content
        else:
            logging.warning("cached tasks summary found")
            mapped_results =  summary_without_img
            projectreportstatus =  project_report_status(max_tasks = len(mapped_results),
                                                          key= check_if_processing_key,
                                                          processed_tasks= len( mapped_results),
                                                          num_task_errors=  list(map(lambda x: x.get("error") , mapped_results)).count(True),
                                                          num_summary_errors= 0,
                                                          num_dronereport_errors= 0,
                                                          status= status_enum.SUMMARIZING_PROJECT.value,
                                                          file_summary= None,
                                                          latest_analysis=  None)


            cache.set(check_if_processing_key ,projectreportstatus, timeout=60*60*10)
            if len(encoding.encode(json.dumps(mapped_results))) < 100000:
                logging.warning("generating project summary")
                summary_state =  {"messages" : json.dumps(mapped_results) + + f"\n total_tasks : {len(mapped_results)}",  "mode": "default" , "task_type": "proj_sum" ,   "status": projectreportstatus}

            else:
                half_task_results =  len(mapped_results) // 4
                tasks_results =  [mapped_results[:half_task_results]  , mapped_results[half_task_results: 2*half_task_results] ,
                                mapped_results[2*half_task_results: 3*half_task_results] , mapped_results[3*half_task_results: ] ]
                chunk_summary_state =  [{"messages" : json.dumps(results) + f"\n total_tasks : {len(results)}", "mode": "default" , "task_type": "proj_sum", "status": projectreportstatus } for results in tasks_results]
                chunk_summary = project_report_service(chunk_summary_state)
                mapped_chunk_results =  list(map(lambda x: {"analysis": x.get("messages")[-1].content,
                                                "error": x.get("messages")[-1].error if hasattr(x.get("messages")[-1], "error") else False}, chunk_summary ))
               
                summary_state =  {"messages" : json.dumps(mapped_chunk_results) + f"\n total_tasks : {len(mapped_results)}", "mode": "default","task_type": "proj_sum", "status": projectreportstatus}
            
            if saved_img_paths:
                logging.warning('found attached imaged, resummarizing with image context')
                summary_state["img_paths"] = saved_img_paths
                summary_state["mode"] = "img"

            final_summary =  project_report_service([summary_state])[0].get("messages")[-1] #pass summary_state to llm and get overall project delay analysis 
            [os.remove(img_path) if os.path.exists(img_path) else None  for img_path in saved_img_paths ]
            logging.warning("analysis completed [project report]")
            if not hasattr(final_summary , "error"):
               final_summary = final_summary.content
               projectreportstatus = cache.get(check_if_processing_key)
               projectreportstatus =  project_report_status(**projectreportstatus)
               projectreportstatus.file_summary = final_summary
               cache.set(check_if_processing_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 5 hrs
            else:
                cache.set(check_if_processing_key , None , timeout=2)
                return final_summary.content
            

        projectreportstatus = cache.get(check_if_processing_key)
        if projectreportstatus:
            projectreportstatus =  project_report_status(**projectreportstatus)
            #projectreportstatus.status = status_enum.COMPLETED.value
            save_tasks(other_tasks = ["delay_analysis", "sch_opt" , "risk_forecast" , "project_report"] ,cache_key =cache_key , xer_key = xer_key ,state = final_summary , report_dict =  projectreportstatus.to_dict())
            #cache.set(cache_key , projectreportstatus.to_dict() , timeout=60*60*10)  # cache for 10 hrs
        else:
            cache.set(cache_key , projectreportstatus, timeout=60*60*10)

        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60 , 2)
        logging.warning(f"analysis completed [project_report] , analysis took {elapsed_time} mins")
        return final_summary
        
def file_hash(file_obj , image_objs = None):
    if image_objs:
       objs =  image_objs + [file_obj]
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
def progress_report_controller(request):
    """Reports general overview of the progress of the xer files, with or without site images """
    parser_classes = [MultiPartParser , FormParser]

    file = request.FILES.get("file")
    images = request.FILES.getlist("image")
    video =  request.FILES.get("video")
    

    if file and file.name.endswith(('.xer')):
        if images:
            filehash =  file_hash(file , images[:10])
        elif video:
            filehash =  file_hash(file , [video])
        elif images and video:
            video = None
            filehash =  file_hash(file , images[:10])   ##Intentionally skipped processing img and video together
        else:
            filehash =  file_hash(file)

        key = cache_key(filehash , "project_report")

        check_if_processing_key = f"{file_hash(file)}:processing"

        xer_hash = file_hash(file)
        xer_key = cache_key(xer_hash, "project_report")
       
        cached_result = cache.get(key)
        if cached_result:
            logging.warning("Returning cached result")
            return Response(cached_result, status=status.HTTP_200_OK)
        elif cache.get(check_if_processing_key):
            return Response(cache.get(check_if_processing_key), status=status.HTTP_202_ACCEPTED)
        else:
            logging.info("No cached file result found, processing file")
            tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)
            logging.warning(f"Processing file: {file.name}")
            file_path = os.path.join(tmp_dir, f"{gen_rand()}_{file.name}")
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            if images:
                if len(images)> 10:
                    images =  images[:10]
                saved_img_paths = []
                for img in images:
                    if img.name.endswith(('.png','.jpg','.jpeg')):
                        tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
                        os.makedirs(tmp_dir, exist_ok=True)
                        logging.warning(f"Processing file: {img.name}")
                        imgfile_path = os.path.join(tmp_dir, f"{gen_rand()}_{img.name}")
                        with open(imgfile_path, 'wb+') as destination:
                            for chunk in img.chunks():
                                destination.write(chunk)
                        saved_img_paths.append(imgfile_path)
                    else:
                       return Response({"error": "image file not valid must be png jpg or jpeg"}, status = status.HTTP_400_BAD_REQUEST)
                t  = report_task.delay(file_path ,xer_key ,key , check_if_processing_key, saved_img_paths = saved_img_paths )
            elif  video:
                if not video.name.endswith(('.mp4','.avi','.mkv')):
                    return Response({"error": "video file not valid must be mp4, avi or mkv"}, status = status.HTTP_400_BAD_REQUEST)
                tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
                os.makedirs(tmp_dir, exist_ok=True)
                logging.warning(f"Processing file: {video.name}")
                videofile_path = os.path.join(tmp_dir, f"{gen_rand()}_{video.name}")
                with open(videofile_path, 'wb+') as destination:
                    for chunk in video.chunks():
                        destination.write(chunk)
                t  = report_task.delay( file_path ,xer_key , key , check_if_processing_key, video_path = videofile_path )
            
            else:
                t =  report_task.delay(file_path ,xer_key , key , check_if_processing_key)

            cache.set(check_if_processing_key , {'task_id': t.id, 'data_key': key , 'status': 'processing'} , timeout=60*60*3)
            return Response({'task_id': t.id, 'data_key': key , 'status': 'processing'}, status=status.HTTP_202_ACCEPTED)
    
    else:
        return Response({"error": "file not valid , only xer file allowed"}, status = status.HTTP_400_BAD_REQUEST)