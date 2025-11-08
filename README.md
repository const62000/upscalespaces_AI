###  UPSCALE AI ENGINE

REQUIREMENTS:
 - ADD OPENAI_API_KEY AND GOOGLE_API_KEY TO .env in *"app/services/.env"*
 - RUN IN LINUX ENVIRONMENT OR PREFERRABLY DOCKER CONTAINER , BUILD DOCKER IMAGE USING THE DOCKER BUILD FILE
 - EXPOSED PORT : 80

## ROUTES

- /delay
  -- ANALYZES FOR DELAY CONSTRAINTS AND POTENTIAL RECOVERY METHODS
  **input_params** : *"file"*: .xer file format only
  **output_code** : *202*: file accepted and processing in background (**out_params** -> 'task_id', 'data_key')
   *400*: Bad request due to error in input 
   *200*: Return Cached analysis response if file was processed successfully in the last 5 hours

- /overall_report
  ANALYZES FOR OVERALL REPORT FOR THE PROJECT
  **input_params** : *"file"* : .xer file format only,*"images"*(Optional): max 10 images of .png , .jpg or .jpeg
  **output_code** : *202*: file accepted and processing in background (**out_params** -> 'task_id', 'data_key')
  *400*: Bad request due to error in input 
  *200*: Return Cached analysis response if file was processed successfully in the last 5 hours

- /risk_forecast
  ANALYZES FOR POTENTIAL RISKS IN THE PROJECT THAT MAY LEAD TO LAGGING
  **input_params** : *"file"*: .xer file format only
  **output_code** : *202*: file accepted and processing in background (**out_params** -> 'task_id', 'data_key')
   *400*: Bad request due to error in input 
   *200*: Return Cached analysis response if file was processed successfully in the last 5 hours

- /schedule_opt
  ANALYZES PROJECT TO OFFER SOLUTION ON BETTER WAY TO ACCOMPLISH OR OPTIMIZE THE PROJECT
  **input_params** : *"file"*: .xer file format only
  **output_code** : *202*: file accepted and processing in background (**out_params** -> 'task_id', 'data_key')
   *400*: Bad request due to error in input 
   *200*: Return Cached analysis response if file was processed successfully in the last 5 hours

- /video_analyzer
  ANALYZES VIDEO INPUT / DRONE FOOTAGES FOR PROGRESS REPORT
   **input_params** : *"file"*: .xer file format only , *"video"*: max 15mins video of .mp4 , .mk4 , .avi
  **output_code** : *202*: file accepted and processing in background (**out_params** -> 'task_id', 'data_key')
   *400*: Bad request due to error in input 
   *200*: Return Cached analysis response if file was processed successfully in the last 5 hours

- /status
  CHECKS THE STATUS OF AN ONGOING OR COMPLETED TASK
  **input_params** : *"task_id"* , *"data_key"*
  **output_code** : *102*: file still processing
  *200*: Return anaysis response if file was processed successfully in the last 5 hours
  *410* : analysis response no longer in memory after processing
  *400*: Bad request due to error in input 



