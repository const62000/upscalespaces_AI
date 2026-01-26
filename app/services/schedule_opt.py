from langchain_core.tools import tool
from langgraph.graph import StateGraph ,MessagesState, END , START
from langchain_core.messages import AIMessage, ToolMessage, AnyMessage
from ..tables_docs import *
from typing_extensions import Annotated
from dotenv import load_dotenv
import logging
from ..prompts.sch_opt import prompt
from .call_llm import call_llm ,  calculator , data_analyst
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.graph.message import add_messages
from api.controllers.schedule_opt_controller import sch_opt_status
from django.core.cache import cache
load_dotenv()
  

class state_schema(MessagesState):
    mode : str    
    task_id: int | None
    status: sch_opt_status
    task_type: str | None
    remaining_steps: RemainingSteps


def tool_node(state: state_schema):  
    logging.warning("tool node called  [sch_opt.py]")
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
    logging.warning("agent node called  [sch_opt.py]")
    msg = state.get("messages")
    mode = state.get("mode")
    task_id = state.get("task_id")
    task_type =  state.get("task_type")

    ai_msg = call_llm(human_input= f"{msg}", mode= mode , task_type= task_type)
    ai_msg["content"] = ai_msg.get("optimization_suggestions")
    ai_msg = AIMessage(**(ai_msg))
    state["messages"].append(ai_msg)
    return state

def route(state: state_schema):
    if state["messages"][-1].tool_calls and state["remaining_steps"] >2:
        return "tools"
    else:
        return "write_status"


def write_status_node(state: state_schema):
    logging.warning("write status node called  [sch_opt.py]")
    task_type =  state.get("task_type")
    status = state.get("status")
    message = state.get("messages")[-1]
    if task_type != "proj_sum":
        if hasattr(message, "error"):
            status.num_task_errors +=1
        status.processed_tasks +=1
    else:
        if hasattr(message, "error"):
            status.num_summary_errors +=1
    status.latest_analysis = message.model_dump()
    cache.set(status.key , status.to_dict() , timeout=60*60*10)
    logging.warning(f"updated status in cache [sch_opt.py]")
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




def _schedule_opt_service(state: list):
    res =  app.batch(state , {"recursion_limit": 20 , "max_concurrency": 4})
    return res

def schedule_opt_service(states:list):
    logging.warning("schedule optimization service called")
    results =  _schedule_opt_service(states)
    return results
    

    


