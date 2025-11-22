from langchain_core.tools import tool

@tool
def rsrc_ref(arguments:str ):

    """useful when you need meaning of column names in the Rsrc table"""
    return f'''
    ---------------------------------------------------------------
    | RSRC - (Resources)              | P6 EPPM Field / Column Name                |
    ---------------------------------------------------------------
    | active_flag                     | Active                                     |
    | auto_compute_act_flag           | Auto Compute Actuals                       |
    | clndr_id                        | Calendar                                   |
    | cost_qty_type                   | Price Time Units                           |
    | curr_id                         | Currency Name                              |
    | def_cost_qty_link_flag          | Calculate Costs from Units                 |
    | def_qty_per_hr                  | Default Units / Time                       |
    | email_addr                      | Email Address                              |
    | employee_code                   | Employee ID                                |
    | guid                            | Global Unique ID                           |
    | location_id                     | Resource Location                          |
    | office_phone                    | Office Phone                               |
    | ot_factor                       | Overtime Factor                            |
    | ot_flag                         | Overtime Allowed                           |
    | other_phone                     | Other Phone                                |
    | parent_rsrc_id                  | Parent Resource                            |
    | role_id                         | Primary Role                               |
    | rsrc_id                         | Unique ID                                  |
    | rsrc_name                       | Resource Name                              |
    | rsrc_notes                      | Resource Notes                             |
    | rsrc_seq_num                    | Sort Order                                 |
    | rsrc_short_name                 | Resource ID                                |
    | rsrc_title_name                 | Title                                      |
    | rsrc_type                       | Resource Type                              |
    | shift_id                        | Shift                                      |
    | timesheet_flag                  | Uses Timesheets                            |
    | ts_approve_user_id              | Timesheet Approval Manager                 |
    | unit_id                         | Unit of Measure                            |
    | user_id                         | User Login Name                            |
    | xfer_complete_day_cnt           | Not-Started Activities View Window (P6 Professional only) |
    | xfer_notstart_day_cnt           | Completed Activities View Window (P6 Professional only)   |
    ---------------------------------------------------------------

    '''