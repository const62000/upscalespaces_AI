from collections import defaultdict
import json
from datetime import datetime
import logging

class construct_table():
    def __init__(self , xer_doc , mode = "default"):
        self.xer_doc =  xer_doc
        self.table_names: list =  self.xer_doc.get_table_names()
        self.ordered_dict = defaultdict(list)
        #tables needed : PROJECT , PROJWBS , TASK , TASKPRED , RSRC , TASKRSRC , CALENDAR
        
        self.file_name =  self.xer_doc.file_name
        self.project_ids = self.proj_id =  [ k for k, v in json.loads(self.xer_doc.to_json('PROJECT'))
                             [self.file_name]['PROJECT'].items()]
        self.mode = mode
    def project(self):
        prj_object =  {}
        prj =  self.xer_doc.to_json('PROJECT')
        prj =  json.loads(prj)
        prj =  [ v for k, v in prj.get(self.file_name).get('PROJECT').items()]
        

        months_id ={"1": "jan" ,  "2": "feb" ,  "3": "march",
                    "4": "apr" ,  "5": "may" ,  "6": "june",
                    "7": "july" , "8": "aug" ,  "9": "sept",
                    "10":"oct" ,  "11": "nov" , "12": "dec"}
        p_object =  []
        for p in prj:
            obj =  {
                "proj_id" : p.get("proj_id"),
                "proj_name": p.get("proj_short_name"),
                "planned_start_date": p.get("plan_start_date"),
                "planned_end_date": p.get("plan_end_date"),
                "schedule_finish_date": p.get("scd_end_date"),
                "calendar_id": p.get("clndr_id"),
                "proj_baseline_id": p.get("sum_base_proj_id"),
                "last_recalc_date": p.get("last_schedule_date") if p.get("last_schedule_date") else p.get("last_recalc_date"),
                "critical_activities_dtype": p.get("critical_path_type"),
                "max_critical_activities": p.get("critical_drtn_hr_cnt"),
                "rate_type": p.get("def_rate_type"),
                "resource_multi_assign": p.get("rsrc_multi_assign_flag"),
                "risk_level": p.get("risk_level"),
                "use_prj_baseline" : p.get("use_project_baseline_flag"),
                "last_baseline_update": p.get("last_baseline_update_date"),
                "fiscal_year_month_beginning": months_id.get(str(p.get("fy_start_month_num"))) if p.get("fy_start_month_num") else None,

            }
            p_object.append(obj)
            prj_object[f'project_id_{p.get("proj_id")}'] = p_object
        
        return prj_object
    
    def proj_wbs(self):
        prj_object ={}
        prj =  self.xer_doc.to_json('PROJWBS')
        prj =  json.loads(prj)
        
        for i , P in enumerate(self.project_ids):
            wbs_object =  []
            prj =  [v  for k ,v in prj.get(self.file_name).get('PROJWBS').items()]
            for p in prj:
                obj =  {
                    "wbs_id" : p.get("wbs_id"),
                    "parent_wbs_id": p.get("parent_wbs_id"),
                    "proj_id": p.get("proj_id"),
                    "obs_id": p.get("obs_id"),
                    "wbs_name": p.get("wbs_name"),
                    "wbs_short_name": p.get("wbs_short_name"),
                    "wbs_status_code": p.get("status_code").split("_")[-1],
                    "seq_num" : p.get("seq_num"),
                    "anticip_start_date": p.get("anticip_start_date"),
                    "anticip_end_date": p.get("anticip_end_date"),
                    "orig_budget": p.get("orig_cost"),
                    "indep_remain_total_cost": p.get("indep_remain_total_cost"),
                    "indep_remain_work_qty" : p.get("indep_remain_work_qty"),

                } 
                wbs_object.append(obj)
            prj_object[f"project_id_{P}"] =  wbs_object

        return prj_object  
    

    def task(self):
        """
        - Tasks filtered by only TT_Task and TT_Rsrc
        - Filters out redundant task_name 
        - if mode is 'delay', only filters out "not completed" tasks

        """
        prj =  self.xer_doc.to_json('TASK')
        prj =  json.loads(prj)
        prj =  [v  for k ,v in prj.get(self.file_name).get('TASK').items()]
        prj_object = {}
        for P in self.project_ids:
            task_obj = []
            task_names ={}
            for p in prj:
                if self.mode =="delay" and p.get("status_code") == "TK_Complete":
                    continue
                if p.get("task_type") == "TT_Task" or "TT_Rsrc":
                    if p.get("task_name") in task_names.keys() and not None:
                        d1  =  datetime.strptime(task_names[p.get("task_name")] , "%Y-%m-%d %H:%M")
                        d2  =  datetime.strptime(p.get("target_start_date"), "%Y-%m-%d %H:%M") 
                        if d2 > d1:
                            for i , o in enumerate(task_obj):
                                if o.get("task_name") ==p.get("task_name") :
                                    task_obj.pop(i)
                                break
                            #logging.warning("Found duplicate task name, replacing with the most recent start date")
                            obj ={
                            "task_id": p.get("task_id"),
                            "proj_id": p.get("proj_id"),
                            "wbs_id": p.get("wbs_id"),
                            "clndr_id": p.get("clndr_id"),
                            "resource_id": p.get("rsrc_id"),
                            "task_code": p.get("task_code"),
                            "task_name": p.get("task_name"),
                            "task_type": p.get("task_type"),
                            "planned_start": p.get("target_start_date"),
                            "planned_end": p.get("target_end_date"),
                            "actual_start": p.get("act_start_date"),
                            "actual_end": p.get("act_end_date"),
                            "early_start_date" : p.get("early_start_date"),
                            "early_end_date": p.get("early_end_date"), 
                            "late_start_date": p.get("late_start_date"),
                            "late_end_date" : p.get("late_end_date"),
                            "PM_expect_end_date": p.get("expect_end_date"),
                            "restart_date": p.get("restart_date"),
                            "reend_date": p.get("reend_date"),
                            "rem_late_start_date": p.get("rem_late_start_date"),
                            "rem_late_end_date": p.get("rem_late_end_date"),
                            "remaining_duration" : p.get("remain_drtn_hr_cnt") if int(float(p.get("remain_drtn_hr_cnt"))) != 0 else None,
                            "planned_duration": p.get("target_drtn_hr_cnt") if int(float(p.get("target_drtn_hr_cnt"))) != 0 else None,
                            "total_float": p.get("total_float_hr_cnt"),
                            "free_float": p.get("free_float_hr_cnt"),
                            "physical_percent_complete": f"{p.get('phys_complete_pct')} %",
                            "status": p.get("status_code").split("_")[-1]}

                            task_names[p.get("task_name")] = p.get("target_start_date")
                            task_obj.append(obj)   
                            
                        else:
                           continue
                    else:
                        obj ={
                            "task_id": p.get("task_id"),
                            "proj_id": p.get("proj_id"),
                            "wbs_id": p.get("wbs_id"),
                            "clndr_id": p.get("clndr_id"),
                            "resource_id": p.get("rsrc_id"),
                            "task_code": p.get("task_code"),
                            "task_name": p.get("task_name"),
                            "task_type": p.get("task_type"),
                            "planned_start": p.get("target_start_date"),
                            "planned_end": p.get("target_end_date"),
                            "actual_start": p.get("act_start_date"),
                            "actual_end": p.get("act_end_date"),
                            "early_start_date" : p.get("early_start_date"),
                            "early_end_date": p.get("early_end_date"), 
                            "late_start_date": p.get("late_start_date"),
                            "late_end_date" : p.get("late_end_date"),
                            "PM_expect_end_date": p.get("expect_end_date"),
                            "restart_date": p.get("restart_date"),
                            "reend_date": p.get("reend_date"),
                            "rem_late_start_date": p.get("rem_late_start_date"),
                            "rem_late_end_date": p.get("rem_late_end_date"),
                            "remaining_duration" : p.get("remain_drtn_hr_cnt") if int(float(p.get("remain_drtn_hr_cnt"))) != 0 else None,
                            "planned_duration": p.get("target_drtn_hr_cnt") if int(float(p.get("target_drtn_hr_cnt"))) != 0 else None,
                            "total_float": p.get("total_float_hr_cnt"),
                            "free_float": p.get("free_float_hr_cnt"),
                            "physical_percent_complete": f"{p.get('phys_complete_pct')} %",
                            "status": p.get("status_code").split("_")[-1]

                        }
                        task_names[p.get("task_name")] = p.get("target_start_date")
                        task_obj.append(obj)
                else:
                    continue
            prj_object[f"project_id_{P}"] = task_obj
        return prj_object


    def task_pred(self):

        prj =  self.xer_doc.to_json('TASKPRED')
        prj =  json.loads(prj)
        prj =  [v  for k ,v in prj.get(self.file_name).get('TASKPRED').items()]
        prj_object = {}

        for P in self.project_ids:
            taskpred_obj = []
            for p in prj:
                obj = {
                    "task_pred_id": p.get("task_pred_id"),
                    "task_id": p.get("pred_task_id"),
                    "successor_task_id": p.get("task_id"),
                    "predecessor_proj_id": p.get("pred_proj_id"),
                    "successor_proj_id": p.get("proj_id"),
                    "lag": p.get("lag_hr_cnt")

                }
                taskpred_obj.append(obj)
            
            prj_object[f"project_id_{P}"] = taskpred_obj



        return prj_object

    def rsrc (self):

        prj =  self.xer_doc.to_json('RSRC')
        prj =  json.loads(prj)
        prj =  [v  for k ,v in prj.get(self.file_name).get('RSRC').items()]
        prj_object = {}
        for P in self.project_ids:
            rsrc_obj = []
            for p in prj:
                obj = {
                    "rsrc_id" :  p.get("rsrc_id"),
                    "rsrc_name" : p.get("rsrc_name"),
                    "rsrc_short_name": p.get("rsrc_short_name"),
                    "rsrc_type": "material" if p.get("rsrc_type") == "RT_Mat" else p.get("rsrc_type").split("_")[-1] ,
                    "cldr_id": p.get("clndr_id"),
                    "role_id": p.get("role_id"),
                    "unit_id": p.get("unit_id"),
                    "def_qty_per_hr": f"{p.get('def_qty_per_hr')} per hour",
                    "curr_id": p.get("curr_id"),
                    "cost_qty_type": p.get("cost_qty_type")
                }
                rsrc_obj.append(obj)
            
            prj_object[f"project_id_{P}"] = rsrc_obj



        return prj_object
    
    def task_rsrc (self):

        prj =  self.xer_doc.to_json('TASKRSRC')
        prj =  json.loads(prj)
        prj =  [v  for k ,v in prj.get(self.file_name).get('TASKRSRC').items()]
        prj_object = {}
        for P in self.project_ids:
            taskrsrc_obj = []
            for p in prj:
                obj = {
                    "taskrsrc_id" :  p.get("taskrsrc_id"),
                    "task_id": p.get("task_id"),
                    "proj_id": p.get("proj_id"),
                    "rsrc_id": p.get("rsrc_id"),
                    "role_id": p.get("role_id"),
                    "target_start_date": p.get("target_start_date"),
                    "act_start_date": p.get("act_start_date"),
                    "target_end_date": p.get("target_end_date"),
                    "act_end_date": p.get("act_end_date"),
                    "restart_date": p.get("restart_date"),
                    "reend_date": p.get("reend_date"),
                    "rem_late_start_date": p.get("rem_late_start_date"),
                    "rem_late_end_date": p.get("rem_late_end_date"),
                    "target_qty": p.get("target_qty"),
                    "act_reg_qty": p.get("act_reg_qty"),
                    "remain_qty": p.get("remain_qty"),
                    "target_qty_per_hr": p.get("target_qty_per_hr"),
                    "remain_qty_per_hr": p.get("remain_qty_per_hr"),
                    "target_cost": p.get("target_cost") if abs(p.get("target_cost"))>0 else None,
                    "act_reg_cost":p.get("act_reg_cost") if abs(p.get("act_reg_cost"))>0 else None,
                    "remain_cost": p.get("remain_cost") if abs(p.get("remain_cost"))>0 else None,
                    "rollup_dates_flag": p.get("rollup_dates_flag"),
                    "rate_type": p.get("rate_type"),
                    "skill_level": p.get("skill_level")
                    
                }
                taskrsrc_obj.append(obj)
            
            prj_object[f"project_id_{P}"] = taskrsrc_obj
        return prj_object 

    
    def calendar (self):

        prj =  self.xer_doc.to_json('CALENDAR')
        prj =  json.loads(prj)
        prj = [v  for k ,v in prj.get(self.file_name).get('CALENDAR').items()]
        prj_object = {}
        for P in self.project_ids:
            calendar_obj = []
            for p in prj:
                obj = {
                    "clndr_id": p.get("clndr_id"),
                    "proj_id": p.get("proj_id"),
                    "clndr_name": p.get("clndr_name"),
                    "clndr_type": p.get("clndr_type"),
                    "base_clndr_id": p.get("base_clndr_id"),
                    "day_hr_cnt": p.get("day_hr_cnt"),
                    "week_hr_cnt": p.get("week_hr_cnt"),
                    "month_hr_cnt": p.get("month_hr_cnt"),
                    "year_hr_cnt": p.get("year_hr_cnt")
                }
                calendar_obj.append(obj)
            
            prj_object[f"project_id_{P}"] = calendar_obj



        return prj_object

    def unified(self):
        if "PROJECT" in self.table_names:
           projects = self.project().get(f"project_id_{self.proj_id[0]}")
           project_by_id = {row["proj_id"]: row for row in projects}
        else:
            projects =[]
            project_by_id ={}
        if "PROJWBS" in self.table_names:
           proj_wbs = self.proj_wbs().get(f"project_id_{self.proj_id[0]}")
           wbs_by_id = {row["wbs_id"]: row for row in proj_wbs}
        else:
             proj_wbs =[]
             wbs_by_id = {}
        if "TASK" in self.table_names:
           tasks:list = self.task().get(f"project_id_{self.proj_id[0]}")  #contains list[dict] of all tasks
           task_by_id = {row["task_id"]: row for row in tasks}
        else:
            tasks = []
            task_by_id ={}
        if "TASKPRED" in self.table_names:
           task_preds = self.task_pred().get(f"project_id_{self.proj_id[0]}")
           tp_by_id = {row["task_id"]: row for row in task_preds}
        else:
            task_preds =[]
            tp_by_id ={}
        if "RSRC" in self.table_names:
           rsrcs = self.rsrc().get(f"project_id_{self.proj_id[0]}")
           rsrc_by_id = {row["rsrc_id"]: row for row in rsrcs}
        else:
            rsrcs =[]
            rsrc_by_id ={}
        if "TASKRSRC" in self.table_names:
           task_rsrcs = self.task_rsrc().get(f"project_id_{self.proj_id[0]}")
           taskrsrc_by_id = {row["rsrc_id"]: row for row in task_rsrcs}
        else:
            task_rsrcs =[]
            taskrsrc_by_id ={}
        if "CALENDAR" in self.table_names:
           calendars = self.calendar().get(f"project_id_{self.proj_id[0]}")
           cal_by_id = {row["clndr_id"]: row for row in calendars}
        else:
            calendars = []
            cal_by_id ={}

        if tasks:
            for task in tasks:
                wbs_id = task.get("wbs_id")
                task_id =  task.get("task_id")
                proj_id = task.get("proj_id")
        
                if wbs_by_id and (wbs_id in wbs_by_id.keys()):
                    task["wbs"] = wbs_by_id[wbs_id]
                if tp_by_id and (task_id in tp_by_id.keys()):
                    task["taskpred"] =  tp_by_id[task_id]
                if project_by_id and (proj_id in project_by_id.keys()):
                    task["project"] =  project_by_id[proj_id]


        
        task_resources = {}  ##contains taskrsrcs + resources  .. task_id is dict key
        if task_rsrcs:
            for tr in task_rsrcs:
                rsrc: int = tr.get("rsrc_id")
                if rsrc:
                    clndr_id = taskrsrc_by_id[rsrc].get("clndr_id")
                    if clndr_id in cal_by_id.keys():
                        tr["calendar"] = cal_by_id[clndr_id]
            for tr in task_rsrcs:
                task_id = tr.get("task_id")
                rsrc_id = tr.get("rsrc_id")
                
                if task_id and rsrc_by_id and task_by_id and (task_id in task_by_id):
                    rs =  rsrc_by_id[rsrc_id]
                    tr["rsrc_name"] = rs.get("rsrc_name")
                    tr["rsrc_short_name"] =  rs.get("rsrc_short_name")
                    tr["rsrc_type"] = rs.get("rsrc_type")
                    tr["def_qty_per_hr"] =  rs.get("def_qty_per_hr")
                    tr["cost_qty_type"] =  rs.get("cost_qty_type")
    
    
                    task_resources[task_id] =  tr

        if tasks:
            for task in tasks:
                task_id = task["task_id"]
                if task_resources:
                   task["task_resources"] = task_resources.get(task_id)
    
            for task in tasks:
                clndr_id = task.get("clndr_id")
                if cal_by_id and (clndr_id in cal_by_id):
                    task["calendar"] = cal_by_id[clndr_id]
              
          
            for t in tasks:
                self.ordered_dict[f"wbs_id_{t['wbs_id']}"].append(t)
        ##summary : tasks is fact table , list[dict] that contains "wbs", "taskpred"[opt] , "project", "task_rsrc:tskrsrc + rsrc"[opt] , "calendar"
        #ordered dict : tasks are grouped by wbs_id
        return tasks ,  self.ordered_dict   ##tasks: list ,  ordered_dict : dict




    