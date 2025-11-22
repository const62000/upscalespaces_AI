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




encoding = tiktoken.get_encoding("cl100k_base")

@shared_task(queue = "drone_queue" , rate_limit='10/m')  ##controls num of request, that can be made.. if it surpasses 5 it lines it up in queue
def drone_task(file_path: str , xer_key , cache_key , video_path: str, check_if_processing_key:str ):
        from app.services.project_report import project_report_service
        from app.services.video_analyzer import video_analyzer
        start_time = time.time()
        summary_without_video = cache.get(xer_key)
        
        if not summary_without_video:
            xer_doc = xer_parser(file_path)  #List
            structured_doc =  construct_table(xer_doc)
            _ , tasks_grouped = structured_doc.unified() # list of unified table per task, filtered by wbs

            if os.path.exists(file_path):
               os.remove(file_path)
            if not tasks_grouped:
               return "No tasks found in the provided xer file."

            analysis = {}
            completed_wbs = 0
            error_count = 0
            for wbs_id , tasks in tasks_grouped.items():
                task_tokens = encoding.encode(json.dumps(tasks))
                logging.warning(f"Processing WBS_ID: {wbs_id} with {len(tasks)} tasks, total tokens: {len(task_tokens)}")
                if len(task_tokens) <= 15000:
                    msg =  f"WBS_ID:{wbs_id} \n\n tasks: {json.dumps(tasks)}"
                    state =  {"messages" : msg , "mode": "wbs"}
                    out =  project_report_service(state)
                    analysis[wbs_id] = out.content
                    completed_wbs+=1
                    if hasattr(out , "error"):
                        error_count+=1
                    logging.warning(f"{completed_wbs} WBSs processed / {len(tasks_grouped.keys())} [drone report]")
                    cache.set(f"{cache_key}_progress" , {'processed_wbs': completed_wbs , 
                                                     'total_wbs': len(tasks_grouped.keys()) , 
                                                     'num_error': error_count} , timeout=60*60*2)
                else:
                    half_task =  len(tasks) // 2
                    tasks =  [tasks[:half_task]  , tasks[half_task:]]
                    t_combined  =  ""
                    for i , t in enumerate(tasks):
                        msg =  f"WBS_ID:{wbs_id}:[chunk {i+1}] \n\n tasks: {json.dumps(t)}"
                        state =  {"messages" : msg , "mode": "wbs"}
                        out =  project_report_service(state)
                        t_combined+=  f"[chunk {i+1}]: \n\n" + out.content+"\n\n"
                    analysis[wbs_id] =t_combined
                    completed_wbs+=1
                    if hasattr(out , "error"):
                        error_count+=1
                    logging.warning(f"{completed_wbs} WBSs processed / {len(tasks_grouped.keys())} [drone report]")
                    cache.set(f"{cache_key}_progress" , {'processed_wbs': completed_wbs , 
                                                     'total_wbs': len(tasks_grouped.keys()) , 
                                                     'num_error': error_count} , timeout=60*60*2)
            #->> after all wbs analysis ->> summarize project delay analysis

            if len(encoding.encode(json.dumps(analysis))) <  230000:
                logging.warning("generating project summary")
                summary_state =  {"messages" : json.dumps(analysis) , "mode": "summary_1" , "task_type": "proj_sum"}

            else:
                logging.warning("generating project summary in 2 chunks due to token size")
                half_wbs =  len(analysis) // 2
                wbs =  [list(analysis.items())[:half_wbs]  , list(analysis.items())[half_wbs:]]
                wbs_combined  =  ""
                for i , w in enumerate(wbs):
                    msg =  f"WBS Analysis:[chunk {i+1}] \n\n wbs_analysis: {json.dumps(dict(w))}"
                    state =  {"messages" : msg , "mode": "summary_1", "task_type": "proj_sum"}
                    wbs_combined+=  f"[chunk {i+1}]: \n\n" + project_report_service(state).content+"\n\n"
                summary_state =  {"messages" : wbs_combined , "mode": "summary_1" , "task_type": "proj_sum"}
            

            final_summary =  project_report_service(summary_state) #pass summary_state to llm and get overall project delay analysis 
            logging.warning("analysis completed  (w/o video) [drone report]")
            if not hasattr(final_summary , "error"):
               cache.set(xer_key , final_summary.content , timeout=60*60*5)  #cache final summary w/o + video summary
               final_summary = final_summary.content
            else:
                cache.set(check_if_processing_key , None , timeout=2)
                return final_summary.content
        else:
            logging.warning("cached proj summary found **[w/o drone footage]")
            final_summary =  summary_without_video
        
        
        if video_path:
            logging.warning('found attached video, resummarizing with video context')
            summary_with_video =  cache.get(cache_key) 
            if not summary_with_video:
                final_summary =  video_analyzer({"messages" : final_summary, 
                                                "system_msg": prompt().summary_2() , 
                                                "video_path" : video_path,
                                                "task_type": "proj_sum"})
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