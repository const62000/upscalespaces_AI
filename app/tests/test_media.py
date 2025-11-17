from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from django.conf import settings
import os
from django.urls import reverse
from django.core.cache import cache



@override_settings(TEST_MODE=True)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True,
                   CELERY_TASK_EAGER_PROPOGATES=True)

@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake'
        }})

class test_media_processing(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_dir = os.path.join(settings.BASE_DIR,"app","tests")

        self.file_path = os.path.join(self.base_dir,"test.xer")
        self.vid_path = os.path.join(self.base_dir,"test_vid.mp4")
        self.img_path = os.path.join(self.base_dir,"test_img.png")
        self.img2_path = os.path.join(self.base_dir,"test_img2.png")

        self.urlnames = ["overall_report" ,  "video_analyzer" ]
        self.routes =  [reverse(name) for name in self.urlnames]
    def test_task(self):
        for r in self.routes:
            with open(self.file_path, 'rb') as xer_file:
                response = self.client.post(r, {'file': xer_file, 
                                                'image': [open(self.img_path , 'rb'),open(self.img2_path , 'rb')],
                                                'video': open(self.vid_path , 'rb')}, format='multipart')
            
            self.assertEqual(response.status_code, 202)
            self.assertIn('task_id', response.json())
            self.assertIn('data_key', response.json())
    
    def tearDown(self):
        cache.clear()