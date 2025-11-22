from langchain_core.tools import tool
from langgraph.graph import StateGraph ,MessagesState, END , START
from langchain_core.messages import AIMessage, HumanMessage , SystemMessage , ToolMessage
from ..tables_docs import *
from dotenv import load_dotenv
import logging
from .call_llm import call_llm , calculator , data_analyst
from langgraph.managed.is_last_step import RemainingSteps

load_dotenv()
  


class state_schema(MessagesState):
    image_paths : list[str] 
    system_msg : str
    remaining_steps: RemainingSteps
    task_type: str | None

def tool_node(state: state_schema):  
    logging.warning("tool node called  [image analyzer.py]")
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
    logging.warning("agent node called  [image analyzer.py]")
    msg = state.get("messages") #all tasks linked to wbs_id
    system =  state.get("system_msg")
    img_paths =  state.get('image_paths')
    task_type =  state.get("task_type")
    
    
    ai_msg = call_llm(mode= "img" , human_msg= f"{msg}" , system_msg= system , image_paths= img_paths , task_type = task_type)

    state["messages"].append(AIMessage(**(ai_msg)))
    return state


def route(state):
    if state["messages"][-1].tool_calls and state["remaining_steps"] >2:
        return "tools"
    else:
        return END
    
workflow = StateGraph(state_schema)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")  
workflow.add_conditional_edges( "agent", route,
                            {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")
app = workflow.compile()


def img_analyzer(state: dict)-> AIMessage:
    res =  app.invoke(state , {"recursion_limit": 50})
    return res["messages"][-1]
    

    


