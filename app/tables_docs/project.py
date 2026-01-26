from langchain_core.tools import tool

#@tool
def project_ref(arguments:str): #

    """useful when you need meaning of column names in the project table"""
    return f'''
    -----------------------------------------------------------------------------------------------------------------------------
    | PROJECT - (Projects)                             | P6 EPPM Field / Column Name                                           |
    -----------------------------------------------------------------------------------------------------------------------------
    | acct_id                                          | Default Cost Account                                                  |
    | act_pct_link_flag                                | Link Percent Complete With Actual                                     |
    | act_this_per_link_flag                           | Link Actual to Date and Actual This Period Units and Costs            |
    | add_act_remain_flag                              | Add Actual To Remain                                                  |
    | add_by_name                                      | Added By                                                              |
    | add_date                                         | Date Added                                                            |
    | allow_complete_flag                              | Can Resources Mark Activities Completed                               |
    | allow_neg_act_flag                               | Allow Negative Actual Units                                           |
    | apply_actuals_date                               | Last Apply Actuals Date                                               |
    | base_type_id                                     | Baseline Type                                                         |
    | batch_sum_flag                                   | Enable Summarization                                                  |
    | checkout_date                                   | Date Checked Out                                                     |
    | checkout_flag                                   | Project Check-out Status                                             |
    | checkout_user_id                                | Checked Out By                                                       |
    | chng_eff_cmp_pct_flag                            | Resources Edit Percent Complete (P6 Professional only)                |
    | clndr_id                                        | Default Calendar                                                     |
    | control_updates_flag                             | Status Update Control                                                 |
    | cost_qty_recalc_flag                             | Cost Qty Recalc Flag                                                 |
    | cr_external_key                                 | Content Repository External UUID                                     |
    | critical_drtn_hr_cnt                            | Critical Activities Have Float ≤                                     |
    | critical_path_type                               | Critical Path Type                                                   |
    | def_complete_pct_type                           | Default Percent Complete Type                                        |
    | def_cost_per_qty                                 | Default Price / Unit                                                 |
    | def_duration_type                               | Default Duration Type                                                |
    | def_qty_type                                    | Default Price Time Units                                             |
    | def_rate_type                                   | Rate Type                                                            |
    | def_rollup_dates_flag                           | Drive Activity Dates Default                                         |
    | def_task_type                                   | Default Activity Type                                                |
    | fcst_start_date                                 | Project Forecast Start                                               |
    | fintmpl_id                                      | Financial Period Calendar ID                                         |
    | fy_start_month_num                              | Fiscal Year Begins                                                   |
    | guid                                            | Global Unique ID                                                     |
    | hist_interval                                   | History Interval                                                     |
    | hist_level                                      | History Level                                                        |
    | intg_proj_type                                  | Integrated Project (P6 Professional only)                             |
    | last_baseline_update_date                       | Last Update Date                                                     |
    | last_checksum                                   | Last Checksum                                                        |
    | last_fin_dates_id                               | Financial Period                                                     |
    | last_level_date                                 | Last Leveled Date (only)                                             |
    | last_recalc_date                                | Last Recalc Date (P6 EPPM)                                           |
    | last_schedule_date                              | Last Scheduled Date (P6 EPPM only)                                   |
    | last_tasksum_date                               | Last Summarized Date                                                 |
    | location_id                                     | Project Location                                                     |
    | msp_managed_flag                                | MS Project Managed Flag (P6 Professional only)                       |
    | name_sep_char                                   | Code Separator                                                       |
    | orig_proj_id                                    | Original Project                                                     |
    | plan_end_date                                   | Must Finish By                                                       |
    | plan_start_date                                 | Planned Start                                                        |
    | priority_num                                   | Project Leveling Priority                                            |
    | proj_id                                        | Unique ID                                                            |
    | proj_short_name                                 | Project ID                                                           |
    | proj_url                                       | Project Web Site URL                                                 |
    | project_flag                                   | Project Flag                                                         |
    | px_enable_publication_flag                      | Enable Publication (only)                                            |
    | px_last_update_date                             | Last Time Publish Project Was Run (P6 Professional only)             |
    | px_priority                                    | Publication Priority (P6 EPPM only)                                  |
    | rem_target_link_flag                            | Link Budget and At Completion                                        |
    | reset_planned_flag                              | Reset Original to Remaining                                          |
    | risk_level                                     | Risk Level (P6 Professional only)                                    |
    | rsrc_multi_assign_flag                          | Can Assign Resource Multiple Times to Activity                       |
    | rsrc_self_add_flag                              | Can Resources Assign Selves to Activities                            |
    | scd_end_date                                   | Schedule Finish                                                      |
    | source_proj_id                                 | Source Project                                                       |
    | step_complete_flag                              | Physical Percent Complete Uses Steps Completed                       |
    | strgy_priority_num                              | Strategic Priority                                                   |
    | sum_assign_level                               | Sum Assign Level                                                     |
    | sum_base_proj_id                               | Project Baseline                                                     |
    | sum_data_date                                  | Summarized Data Date (P6 Professional only)                          |
    | sum_only_flag                                  | Contains Summarized Data Only (P6 Professional only)                 |
    | task_code_base                                 | Activity ID Suffix                                                   |
    | task_code_prefix                               | Activity ID Prefix                                                   |
    | task_code_prefix_flag                           | Activity ID Based on Selected Activity                               |
    | task_code_step                                 | Activity ID Increment                                                |
    | ts_rsrc_vs_inact_actv_flag                     | Resource Can View Activities from Inactive Project (P6 Prof only)    |
    | use_project_baseline_flag                      | Use Project Baseline Flag                                            |
    | wbs_max_sum_level                              | WBS Max Summarization Level                                          |
    | web_local_root_path                            | Web Site Root Directory                                              |
    -----------------------------------------------------------------------------------------------------------------------------

    '''