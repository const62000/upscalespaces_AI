from langchain_core.tools import tool

@tool
def projwbs_ref(arguments:str): #

    """useful when you need meaning of column names in the WBS table"""
    return f'''
    ---------------------------------------------------------------------------------------------------------------------
    | PROJWBS - (WBS)                          | P6 EPPM Field / Column Name                               |
    ---------------------------------------------------------------------------------------------------------------------
    | ann_dscnt_rate_pct                       | Annual Discount Rate                                      |
    | anticip_end_date                         | Anticipated Finish                                        |
    | anticip_start_date                       | Anticipated Start                                         |
    | dscnt_period_type                        | Discount Application Period                               |
    | est_wt                                   | Est Weight (P6 Professional only)                         |
    | ev_compute_type                          | Earned Value Percent Complete Technique                   |
    | ev_etc_compute_type                      | Earned Value Estimate-to-Complete Technique               |
    | ev_etc_user_value                        | Earned Value Performance Factor                           |
    | ev_user_pct                              | Earned Value Percent Complete                             |
    | guid                                     | Global Unique ID                                          |
    | indep_remain_total_cost                  | Independent ETC Total Cost                                |
    | indep_remain_work_qty                    | Independent ETC Labor Units                               |
    | obs_id                                   | Responsible Manager                                       |
    | orig_cost                                | Original Budget                                           |
    | parent_wbs_id                            | Parent WBS                                                |
    | phase_id                                 | WBS Category                                              |
    | proj_id                                  | Project                                                   |
    | proj_node_flag                           | Project Node                                              |
    | seq_num                                  | Sort Order                                                |
    | status_code                              | Project Status                                            |
    | status_reviewer                          | User Reviewing Status                                     |
    | sum_data_flag                            | Contains Summary Data                                     |
    | tmpl_guid                                | Methodology Global Unique ID                              |
    | wbs_id                                   | Unique ID                                                 |
    | wbs_name                                 | WBS Name                                                  |
    | wbs_short_name                           | WBS Code                                                  |
    ---------------------------------------------------------------------------------------------------------------------
    '''