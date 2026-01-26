from langchain_core.tools import tool

#@tool
def task_pred_ref(arguments:str): #
    """useful when you need meaning of column names in the Taskpred table"""
    return f'''
    ---------------------------------------------------------------
    | TASKPRED - (Activity Relationships) | P6 EPPM Field / Column Name   |
    ---------------------------------------------------------------
    | comments                          | Comments                       |
    | lag_hr_cnt                         | Lag                            |
    | pred_proj_id                       | Predecessor Project             |
    | pred_task_id                       | Predecessor                    |
    | pred_type                          | Relationship Type               |
    | proj_id                            | Successor Project               |
    | task_id                            | Successor                      |
    | task_pred_id                       | Unique ID                      |
    ---------------------------------------------------------------
    '''
