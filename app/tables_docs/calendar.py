from langchain_core.tools import tool

@tool
def calendar_ref(arguments:str): ##
    
    """useful when you need meaning of column names in the calendar table"""
    return f'''
    ----------------------------------------------------------------------------------------------------------
    | CALENDAR - (Calendars)              | P6 EPPM Field / Column Name                     |
    ----------------------------------------------------------------------------------------------------------
    | base_clndr_id                       | Parent Calendar                                |
    | clndr_data                          | Data                                           |
    | clndr_id                            | Unique ID                                     |
    | clndr_name                          | Calendar Name                                 |
    | clndr_type                          | Calendar Type                                 |
    | day_hr_cnt                          | Work Hours Per Day                            |
    | default_flag                        | Default                                       |
    | last_chng_date                      | Date Last Changed                             |
    | month_hr_cnt                        | Work Hours Per Month                          |
    | proj_id                             | Project                                       |
    | rsrc_private                        | Personal Calendar (P6 EPPM only)              |
    | week_hr_cnt                         | Work Hours Per Week                           |
    | year_hr_cnt                         | Work Hours Per Year                           |
    ----------------------------------------------------------------------------------------------------------
    '''