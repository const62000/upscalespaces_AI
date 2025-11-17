from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from django.conf import settings
import os
from django.urls import reverse
from django.core.cache import cache
'''


@override_settings(TEST_MODE=True)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True,
                   CELERY_TASK_EAGER_PROPOGATES=True)

@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake'
        }})

class test_file_processing(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_dir = os.path.join(settings.BASE_DIR,"app","tests","test.xer")
        self.urlnames = ["risk_forecast" ,  "delay" , "schedule_opt"]
        self.routes =  [reverse(name) for name in self.urlnames]
    def test_task(self):
        for r in self.routes:
            with open(self.base_dir, 'rb') as xer_file:
                response = self.client.post(r, {'file': xer_file}, format='multipart')
            
            self.assertEqual(response.status_code, 202)
            self.assertIn('task_id', response.json())
            self.assertIn('data_key', response.json())
    
    def tearDown(self):
        cache.clear()
'''