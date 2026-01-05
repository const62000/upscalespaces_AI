from langchain_core.tools import tool
from langgraph.graph import StateGraph ,MessagesState, END , START
from langchain_core.messages import AIMessage, ToolMessage, AnyMessage
from ..tables_docs import *
from typing_extensions import Annotated
from dotenv import load_dotenv
import logging
from ..prompts.proj_report import prompt
from .call_llm import call_llm , calculator , data_analyst
import secrets
import string
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.graph.message import add_messages
from api.controllers.project_report_controller import project_report_status
from django.core.cache import cache

load_dotenv()
  

def gen_rand():
    return ''.join(secrets.choice(string.digits) for _ in range(15))

     
class state_schema(MessagesState):
    mode : str    
    remaining_steps: RemainingSteps
    task_type: str | None
    task_id: int | None
    status: project_report_status


def tool_node(state: state_schema):  
    logging.warning("tool node called  [project_report.py]")
    tools =  [calculator ,  data_analyst,calendar_ref,
              project_ref,  projwbs_ref ,  rsrc_ref,
              task_rsrc_ref , task_pred_ref ,  task_ref]
    ref_tools = ["calendar_ref","project_ref",  "projwbs_ref",  "rsrc_ref",
                "task_rsrc_ref" , "task_pred_ref" ,  "task_ref"]
   
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return state 

    for call in tool_calls:
        tool_name = call["name"]
        if tool_name in ref_tools:
            tool =  next(t for t in tools if t.name == tool_name)
            try:
                result = tool.invoke({"arguments" : "none"})
            except Exception as e:
                result = ToolMessage(content =  f"failed to use {call.get('name')} tool at this time" , tool_call_id = "none")
                logging.warning(f"failed to use {call.get('name')} tool at this time")
            state["messages"].append(result)
        else:
            tool =  next(t for t in tools if t.name == tool_name)

            if call.get("args").get("arguments") is None:
               result = ToolMessage(content =  f"failed to use {call.get('name')} tool at this time" , tool_call_id = "none")
               logging.warning(f"failed to use {call.get('name')} tool at this time, missing arguments")
               state["messages"].append(result)
               continue
            else:
                try:
                   result =  tool.invoke({"arguments" : call["args"]["arguments"]})
                except:
                    result = ToolMessage(content =  f"failed to use {call.get('name')} tool at this time" , tool_call_id = "none")
                    logging.warning(f"failed to use {call.get('name')} tool at this time")
                state["messages"].append(result)
            
    return state

def agent_node(state: state_schema):
    logging.warning("agent node called  [project_report.py]")
    msg = state.get("messages") #all tasks linked to wbs_id
    mode = state.get("mode")  #task or summary   ***
    task_type = state.get("task_type") #
    
    system =  prompt().wbs() if mode == "task" else prompt().summary_1()

    
    ai_msg = call_llm(mode= "default" , human_msg= f"{msg}" , system_msg= system , task_type =task_type)

    state["messages"].append(AIMessage(**(ai_msg)))
    return state

def route(state: state_schema):
    if state["messages"][-1].tool_calls and state["remaining_steps"] >2:
        return "tools"
    else:
        return "write_status"


def write_status_node(state: state_schema):
    logging.warning("write status node called  [project_report.py]")
    mode =  state.get("mode")
    status = state.get("status")
    message = state.get("messages")[-1]
    summary_modes =  ["summary_1" , "summary_2"]
    if mode not in  summary_modes:
        if hasattr(message, "error"):
            status.num_task_errors +=1
        status.processed_tasks +=1
    else:
        if hasattr(message, "error"):
            status.num_summary_errors +=1
    status.latest_analysis = message.content
    cache.set(status.key , status.to_dict() , timeout=60*60*10)  # cache for 10 hrs
    logging.warning(f"updated status in cache [project_report.py]")
    return state

workflow = StateGraph(state_schema)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("write_status", write_status_node)

workflow.add_edge(START, "agent")  
workflow.add_conditional_edges( "agent", route,
                            {"tools": "tools", "write_status": "write_status"} )
workflow.add_edge("tools", "agent")
app = workflow.compile()





def _project_report_service(state: list):
    res =  app.batch(state , {"recursion_limit": 50 , "max_concurrency": len(state)} , return_exceptions = True )
    return res


def project_report_service(states:list):
    logging.warning("project report service called")
    results =  _project_report_service(states)
    return results
    

    


