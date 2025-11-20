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


encoding = tiktoken.get_encoding("cl100k_base")


@shared_task(queue = "delay_queue" ,rate_limit='10/m')
def delay_task(file_path: str , cache_key:str , check_if_processing_key:str):
        from app.services.delay_analysis import delay_analysis_service
        start_time = time.time()
        xer_doc = xer_parser(file_path)  #List
        structured_doc =  construct_table(xer_doc , mode = "delay")
        _ , tasks_grouped = structured_doc.unified() # list of unified table per task, grouped by wbs_id
        if os.path.exists(file_path):
           os.remove(file_path)
        if not tasks_grouped:
            return "No tasks found in the provided xer file."
        analysis = {}
        completed_wbs = 0
        error_count = 0
        for wbs_id , tasks in tasks_grouped.items():
            task_tokens =  encoding.encode(json.dumps(tasks))
            logging.warning(f"Processing WBS_ID: {wbs_id} with {len(tasks)} tasks, total tokens: {len(task_tokens)}")
            if len(task_tokens) <= 15000:
                msg =  f"WBS_ID:{wbs_id} \n\n tasks: {json.dumps(tasks)}"
                state =  {"messages" : msg , "mode": "wbs"}
                out  =delay_analysis_service(state)
                analysis[wbs_id] = out.content
                completed_wbs+=1
                if hasattr(out , "error"):
                    error_count+=1
                logging.warning(f"{completed_wbs} WBSs processed / {len(tasks_grouped.keys())} [delay analysis]")
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
                    out =  delay_analysis_service(state)
                    t_combined+=  f"[chunk {i+1}]: \n\n" + out.content+"\n\n"
                analysis[wbs_id] =t_combined
                completed_wbs+=1
                if hasattr(out , "error"):
                    error_count+=1
                logging.warning(f"{completed_wbs} WBSs processed / {len(tasks_grouped.keys())} [delay analysis]")
                cache.set(f"{cache_key}_progress" , {'processed_wbs': completed_wbs , 
                                                     'total_wbs': len(tasks_grouped.keys()) , 
                                                     'num_error': error_count} , timeout=60*60*2)
        #->> after all wbs analysis ->> summarize project delay analysis
        if len(encoding.encode(json.dumps(analysis))) <= 230000:
            summary_state =  {"messages" : json.dumps(analysis) , "mode": "summary"}

        else:
            half_wbs =  len(analysis) // 2
            wbs =  [list(analysis.items())[:half_wbs]  , list(analysis.items())[half_wbs:]]
            wbs_combined  =  ""
            for i , w in enumerate(wbs):
                msg =  f"WBS Analysis:[chunk {i+1}] \n\n wbs_analysis: {json.dumps(dict(w))}"
                state =  {"messages" : msg , "mode": "summary"}
                wbs_combined+=  f"[chunk {i+1}]: \n\n" + delay_analysis_service(state).content+"\n\n"
            summary_state =  {"messages" : wbs_combined , "mode": "summary"}
        
        final_summary =  delay_analysis_service(summary_state) #pass summary_state to llm and get overall project delay analysis 
        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60 , 2)  #in mins
        logging.warning(f"analysis completed [delay analysis] , analysis took {elapsed_time} mins")
        if not hasattr(final_summary , "error"):
           cache.set(cache_key, final_summary.content, timeout=60*60*5)  # cache for 5 hrs
        else:
            cache.set(check_if_processing_key , None , timeout=2)
        return final_summary.content

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
def delay_analysis_controller(request):
    """analyzes xer files for delay causes and potential recovery options"""

    parser_classes = [MultiPartParser , FormParser]
    file = request.FILES.get("file")

    if file and file.name.endswith(('.xer')):  
        filehash =  file_hash(file)
        key = cache_key(filehash , "delay_analysis")
        check_if_processing_key = f"{key}:processing"
        cached_result = cache.get(key)
        if cached_result:
            logging.warning("Returning cached result")
            return Response(cached_result, status=status.HTTP_200_OK)
        elif cache.get(check_if_processing_key):
            return Response(cache.get(check_if_processing_key), status=status.HTTP_202_ACCEPTED)
        else:
            logging.warning("No cached result found, processing file")
        
            tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)
            
            logging.warning(f"Processing file: {file.name}")
            file_path = os.path.join(tmp_dir, f"{gen_rand()}_{file.name}")
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
    
            #->> call task function (would be celery function)
            t =  delay_task.delay(file_path , key, check_if_processing_key)
            cache.set(check_if_processing_key , {'task_id': t.id, 'data_key': key , 'status': 'processing'} , timeout=60*60*3)
            return Response({'task_id': t.id, 'data_key': key , 'status': 'processing'}, status=status.HTTP_202_ACCEPTED)
    else:
        return Response({"error": "file not valid, only '.xer' file is allowed"}, status = status.HTTP_400_BAD_REQUEST)
    