import time
from tenacity import retry, wait_random_exponential, stop_after_attempt , wait_exponential_jitter
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from celery import shared_task
import logging
from langchain_core.tools import tool
from ..prompts.tools import prompt
from ..tables_docs import *
import base64
from PIL import Image
from langchain_core.messages import AIMessage, HumanMessage , SystemMessage , ToolMessage
import django_rq
import time
import cv2
from langchain_google_genai import ChatGoogleGenerativeAI
from django.conf import settings
try:
    from decord import VideoReader, cpu  # optional dependency for video processing
    _DECORD_AVAILABLE = True
except ImportError:
    _DECORD_AVAILABLE = False

load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini",temperature=1,max_tokens=800,timeout=None,max_retries=2) 
llm_2 = ChatGoogleGenerativeAI(model="gemini-2.5-flash", max_output_tokens =1500)

@tool
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def calculator(arguments: str):
    """Useful for when you need to perform calculations and arithmetics"""
    logging.warning("calculator tool called")
    messages = [("system",prompt().calculator()),
                ("human", arguments)]

    tool_msg = llm.invoke(messages)
    return tool_msg.content
    


@tool
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def data_analyst(arguments: str):
    """Useful for when you need more deep analysis on the data"""
    logging.warning("data analyst tool called")
    messages = [("system",prompt().data_analyst()),
                ("human", arguments)]
   
    tool_msg = llm.invoke(messages)
    return tool_msg.content
    
    

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def llm_call(mode:str , human_msg: str,  system_msg: str  , image_paths= None , video_path = None):
    if mode == "img":
        logging.warning("calling image analyzer llm")
        tools =  [calculator ,  data_analyst,calendar_ref,
                project_ref,  projwbs_ref ,  rsrc_ref,
                task_rsrc_ref , task_pred_ref ,  task_ref]
        model = llm_2.bind_tools(tools)
        
        human_content =  []
        for img in image_paths:
            Image.open(img).resize([512,512]).save(img , 'JPEG')
            time.sleep(0.5)
            with open(img , "rb") as imgfile:
                img_data =  base64.b64encode(imgfile.read()).decode("utf-8")
                b64_img = f"data:image/jpeg;base64,{img_data}"
                human_content.append({"type": "image_url" , "image_url": {"url": b64_img}})

        human_content.append({"type": "text" , "text": human_msg})      
        
        human_msg =  HumanMessage(content=human_content)
        system_msg =  SystemMessage(content=system_msg)

        messages = [system_msg, human_msg]
        try:
            ai_msg = model.invoke(messages)
            return ai_msg.model_dump()  #as dict
        except Exception as e:
            raise e
    elif mode == "vid":
        logging.warning("calling video analyzer llm")
        if not _DECORD_AVAILABLE:
            raise RuntimeError(
                "decord is not installed. Install 'decord' to enable video analysis."
            )
        fps = 1.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 

        with open(video_path , "rb") as f:
            vr = VideoReader(f, cpu(0) ,  num_threads = 3)
            vr = vr.get_batch(range(0, len(vr), 60)).asnumpy()   #samples at 1 frame per second, assuming its as 60fps video

        frame_size = (vr.shape[2], vr.shape[1])
        out = cv2.VideoWriter(video_path, fourcc, fps, frame_size, isColor=True)
        for frame in vr:
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            out.write(bgr_frame)
        out.release()

        tools =  [calculator ,  data_analyst,calendar_ref,
                project_ref,  projwbs_ref ,  rsrc_ref,
                task_rsrc_ref , task_pred_ref ,  task_ref]
        model = llm_2.bind_tools(tools)
        
        human_content =  []
        
        with open(video_path , "rb") as vid:
            vid_data =  base64.b64encode(vid.read()).decode("utf-8")
            human_content.append({"type": "video" , "video": {"data": vid_data ,  "mime_type": "video/mp4"}})

        human_content.append({"type": "text" , "text": human_msg})      
        
        human_msg =  HumanMessage(content=human_content)
        system_msg =  SystemMessage(content=system_msg)

        messages = [system_msg, human_msg]
        try:
            ai_msg = model.invoke(messages)
            return ai_msg.model_dump()  #as dict
        except Exception as e:
            raise e


    else:
        logging.warning("calling llm")
        tools =  [calculator ,  data_analyst,calendar_ref,
                project_ref,  projwbs_ref ,  rsrc_ref,
                task_rsrc_ref , task_pred_ref ,  task_ref]
        
        model = llm.bind_tools(tools)
        messages = [("system",system_msg),
                    ("human", human_msg)]
        try:
            ai_msg = model.invoke(messages)
            return ai_msg.model_dump()  #as dict
        except Exception as e:
            raise e
    
    

def _call_llm(mode:str , human_msg: str,  system_msg: str  , image_paths:list= None , video_path:str = None)->AIMessage:
    try:
        return llm_call(mode= mode , human_msg= human_msg,  system_msg=system_msg  , 
                        image_paths=image_paths , video_path=video_path)
    except Exception as e:
        logging.warning("error: Failed to generate analysis at this time.")
        return AIMessage(content="error: Failed to generate analysis at this time." , error = True).model_dump()


def call_llm(mode:str , human_msg: str,  system_msg: str  , image_paths:list= None , video_path:str = None):
    if settings.TEST_MODE:
            return _call_llm(mode , human_msg , system_msg , image_paths , video_path)
    
    else:
        media_modes =["vid", "img"]
        if mode in media_modes:
            gemini_queue = django_rq.get_queue('gemini')
            job = gemini_queue.enqueue(_call_llm, mode , human_msg , system_msg , image_paths, video_path )
        else:
            gpt_queue = django_rq.get_queue('gpt')
            job = gpt_queue.enqueue(_call_llm, mode , human_msg , system_msg)

        timeout = 60 * 30 # 30 mins (in secs) timeout
        start = time.time()

        while not job.is_finished and not job.is_failed:
            if (time.time() - start) > timeout:
                logging.warning("error:  Failed to generate analysis at this time. [due to queue timeout error]")
                return AIMessage(content="error: Failed to generate analysis at this time" , error= True).model_dump()
            time.sleep(0.5)
            job.refresh()
        if job.is_failed:
            logging.warning("error: Failed to generate analysis at this time.  [due to failed job in queue]")
            return AIMessage(content="error: Failed to generate analysis at this time." , error=True).model_dump()
        logging.warning(f"Waited for {round(time.time()- start , 2)}s to get LLM result from job")
        ai_msg = job.result
        return ai_msg