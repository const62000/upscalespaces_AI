import dspy
from tenacity import retry, stop_after_attempt, wait_random_exponential
from typing_extensions import TypedDict, Literal , List ,Optional
import logging
from django.conf import settings
from ..tables_docs import *
from ..prompts.tools import prompt
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
import time
import django_rq
import json
from langchain_mistralai import ChatMistralAI

try:
    from decord import VideoReader, cpu  # optional dependency for video processing
    _DECORD_AVAILABLE = True
except ImportError:
    _DECORD_AVAILABLE = False

'''

def get_openai_llm():
    lm_openai =  dspy.LM("mistral/open-mistral-7b" , api_key = settings.ANYSCALE_API_KEY)
    llm= ChatMistralAI(model="mistral-large-latest",max_tokens=800,api_key = settings.ANYSCALE_API_KEY) 
    return lm_openai , llm

def get_gemini_llm():
    lm_openai =  dspy.LM("mistral/open-mistral-7b" , api_key = settings.ANYSCALE_API_KEY)
    llm= ChatMistralAI(model="mistral-large-latest",max_tokens=800, api_key = settings.ANYSCALE_API_KEY) 
    return lm_openai , llm

'''
def get_openai_llm():
    lm_openai =  dspy.LM("openai/gpt-4o" , api_key = settings.GPT_KEY)
    llm = ChatOpenAI(model="gpt-4o", max_tokens =800, api_key = settings.GPT_KEY)
    return lm_openai , llm
def get_gemini_llm():
    lm_gemini =  dspy.LM("gemini/gemini-2.5-flash" , api_key = settings.GEMINI_KEY)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", max_tokens =800, api_key = settings.GEMINI_KEY)
    return lm_gemini , llm


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def calculator(arguments: str):
    """Useful for when you need to perform calculations and arithmetics"""
    logging.warning("calculator tool called")
    messages = [("system",prompt().calculator()),
                ("human", arguments)]
    _, llm =  get_openai_llm()
    tool_msg = llm.invoke(messages)
    return tool_msg.content
    
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def data_analyst(arguments: str):
    """Useful for when you need more deep analysis on the data"""
    logging.warning("data analyst tool called")
    messages = [("system",prompt().data_analyst()),
                ("human", arguments)]
    _, llm =  get_openai_llm()
    tool_msg = llm.invoke(messages)
    return tool_msg.content

class task_analysis_signature(dspy.Signature):
    task : str = dspy.InputField()
    delay_analysis: str = dspy.OutputField(desc =  "report on delay analysis of this particular task showing exact reasons causing delay,and impact on overall project timeline and how to mitigate them")
    risk_forecast: str = dspy.OutputField(desc = "report on risk forecast of this particular task, showing vulnerabilities, their likelihood, impact, and mitigation strategies")
    optimization_suggestions: str = dspy.OutputField(desc =  "report on optimizable suggestions for task to move faster and more cost efficient, pin point pverlooked vulnerabities and show how to optimize them for better outputs")  #schedule optimization suggestions
    overall_review : str = dspy.OutputField(desc =  "overall task review, breaking down key highlights of the most important aspects of the task, current issues, and recommendations for improvement")


class report_schema(TypedDict):
    analysis: str
    avg_percentage_progress: float
    total_tasks: int
    active_tasks: int
    overdue_tasks: int


class overall_project_aggregate_signature(dspy.Signature):
    tasks_summary : str =  dspy.InputField()
    image : Optional[List[object]]  = dspy.InputField()
    video : Optional[object] = dspy.InputField()
    delay_analysis: report_schema =  dspy.OutputField(desc =  "report on delay analysis of overall project showing exact tasks(task_id) causing delay,reasons for delay and impact on overall project timeline")
    risk_forecast: report_schema =  dspy.OutputField(desc = "report on risk forecast of overall project showing particulary tasks(task_id) with high risks, their likelihood, impact, and mitigation strategies")
    optimization_suggestions: report_schema  = dspy.OutputField(desc =  "report on optimizable suggestions for project to move faster and more cost efficiency, pin point vulnerable tasks and show how to optimize them for better outputs")   # schedule optimization suggestions
    overall_review : report_schema = dspy.OutputField(desc =  "overall project review, breaking down key highlights of the most important tasks(task_id) and current tasks, issues, and recommendations for improvement")



class task_analysis_module(dspy.Module):
    def __init__(self):
        super().__init__()
        self.task_understanding = dspy.ChainOfThought("task -> parsed_task: str , task_percent_progress: float")
        self.task_understanding_xx =  dspy.ReAct("task -> parsed_task:str , task_percent_progress: float",
                                                 tools = [dspy.Tool(calculator) ,  dspy.Tool(data_analyst),dspy.Tool(calendar_ref),
                                                      dspy.Tool(project_ref),  dspy.Tool(projwbs_ref) ,  dspy.Tool(rsrc_ref),
                                                      dspy.Tool(task_rsrc_ref) , dspy.Tool(task_pred_ref) ,  dspy.Tool(task_ref)] ,
                                                      max_iters = 25)
        self.overall_task_understanding =dspy.Predict("cot_parsed_task, react_parsed_task -> task_understanding: str")
        self.analysis =  dspy.ChainOfThought(task_analysis_signature)

    def forward(self,task):
        parsed_task =  json.dumps(self.task_understanding(task = task).toDict())
        parsed_task_xx = json.dumps(self.task_understanding_xx(task = task).toDict())
        parsed_task =  self.overall_task_understanding(cot_parsed_task= parsed_task , react_parsed_task= parsed_task_xx).task_understanding
        analysis = self.analysis(task = parsed_task)

        return analysis
    
class overall_project_aggregate_module(dspy.Module):
    def __init__(self):
        super().__init__()
        self.analysis =  dspy.ChainOfThought(overall_project_aggregate_signature)


    def forward(self,tasks_summary: str ,mode:str , img_files: List[str] | None = None , video_file: str | None = None):
        if mode == "img":
            logging.warning("calling image analyzer llm")
            if not img_files:
                logging.warning("no image files provided for analysis")
                analysis = self.analysis(tasks_summary = tasks_summary , image = img_objs , video = video_file)
            img_objs  = []
            for img in img_files:
                Image.open(img).resize([512,512]).save(img , 'JPEG')
                time.sleep(0.5)
                with open(img , "rb") as imgfile:
                    image = imgfile.read()
                img_objs.append(image)
            analysis = self.analysis(tasks_summary = tasks_summary , image = img_objs , video = video_file)
        elif mode == "vid":
            import cv2
            logging.warning("calling video analyzer llm")
            if not _DECORD_AVAILABLE:
                raise RuntimeError(
                    "decord is not installed. Install 'decord' to enable video analysis."
                )
            if not video_file:
                logging.warning("no video file provided for analysis")
                analysis = self.analysis(tasks_summary = tasks_summary , image = None , video = None)
            fps = 1.0
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            with open(video_file , "rb") as f:
                vr = VideoReader(f, cpu(0) ,  num_threads = 3)
                vr = vr.get_batch(range(0, len(vr), 60)).asnumpy()   #samples at 1 frame per second, assuming its as 60fps video
            frame_size = (vr.shape[2], vr.shape[1])
            out = cv2.VideoWriter(video_file, fourcc, fps, frame_size, isColor=True)
            for frame in vr:
                bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                out.write(bgr_frame)
            out.release()
            with open(video_file , "rb") as vf:
                video_data = vf.read()
            analysis = self.analysis(tasks_summary = tasks_summary , image = None , video = video_data)
        else:
            logging.warning("calling default llm")
            analysis = self.analysis(tasks_summary = tasks_summary)
        return analysis

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def llm_call(human_input: str,mode:str , img_files: List[str] | None = None , video_file: str | None = None , task_type = None):
    if img_files or video_file:
        lm ,  _ = get_gemini_llm()
        dspy.configure(lm=lm)
    else:
        lm ,  _ = get_openai_llm()
        dspy.configure(lm=lm)

    
    if task_type != "proj_sum":
        taskanalysismodule =  task_analysis_module()
        try:
           analysis = taskanalysismodule(task = human_input)
           return analysis
        except Exception as e:
              logging.warning(f"task analysis module failed with error: {e}")
              raise e
    else:  
        try:
            overallprojectaggregatemodule = overall_project_aggregate_module()
            analysis = overallprojectaggregatemodule(tasks_summary = human_input , mode= mode , img_files= img_files , video_file= video_file)
            return analysis
        except Exception as e:
              logging.warning(f"overrall project analysis module failed with error: {e}")
              raise e
        

def _call_llm(human_input: str,mode:str , img_files: List[str] | None = None , video_file: str | None = None , task_type = None):
    try:
        analysis = llm_call(human_input= human_input , mode= mode , img_files= img_files , video_file= video_file , task_type = task_type)
        return analysis.toDict()
    except Exception as e:
        logging.warning(f"llm call failed with error: {e}")
        return dspy.Prediction(delay_analysis =  "Failed to generate analysis at this time." ,
                               risk_forecast = "Failed to generate analysis at this time." ,
                               optimization_suggestions = "Failed to generate analysis at this time." ,
                               overall_review = "Failed to generate analysis at this time." ,
                               error = True).toDict()
    

def call_llm(human_input: str,mode:str , img_files: List[str] | None = None , video_file: str | None = None , task_type = None):
    media_modes =["vid", "img"]
    if mode in media_modes:
        gemini_queue = django_rq.get_queue('gemini')
        job = gemini_queue.enqueue(_call_llm,human_input,  mode , img_files, video_file , task_type = task_type)
    else:
        gpt_queue = django_rq.get_queue('gpt')
        job = gpt_queue.enqueue(_call_llm, human_input, mode , img_files, video_file , task_type = task_type)

    timeout = 60 * 30 # 30 mins (in secs) timeout
    start = time.time()
    while not job.is_finished and not job.is_failed:
        if (time.time() - start) > timeout:
            logging.warning("error:  Failed to generate analysis at this time. [due to queue timeout error]")
            return dspy.Prediction(delay_analysis =  "Failed to generate analysis at this time." ,
                               risk_forecast = "Failed to generate analysis at this time." ,
                               optimization_suggestions = "Failed to generate analysis at this time." ,
                               overall_review = "Failed to generate analysis at this time." ,
                               error = True).toDict()
        time.sleep(0.5)
        job.refresh()
    if job.is_failed:
        logging.warning("error: Failed to generate analysis at this time.  [due to failed job in queue]")
        return dspy.Prediction(delay_analysis =  "Failed to generate analysis at this time." ,
                               risk_forecast = "Failed to generate analysis at this time." ,
                               optimization_suggestions = "Failed to generate analysis at this time." ,
                               overall_review = "Failed to generate analysis at this time." ,
                               error = True).toDict()
    logging.warning(f"Waited for {round(time.time()- start , 2)}s to get LLM result from job")
    analysis = job.result
    if isinstance(analysis.get("delay_analysis"), dict):
       analysis["delay_analysis"] =  json.dumps(analysis["delay_analysis"])
    if isinstance(analysis.get("risk_forecast"), dict):
       analysis["risk_forecast"] =  json.dumps(analysis["risk_forecast"])
    if isinstance(analysis.get("optimization_suggestions"), dict):
       analysis["optimization_suggestions"] =  json.dumps(analysis["optimization_suggestions"])
    if isinstance(analysis.get("overall_review"), dict):
       analysis["overall_review"] =  json.dumps(analysis["overall_review"])
    return analysis
