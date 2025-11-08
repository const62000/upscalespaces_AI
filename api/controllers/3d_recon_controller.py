from rest_framework.response import Response 
from rest_framework import status
from rest_framework import serializers
from rest_framework.decorators import api_view
from ..serializers.doc_serializer import docserializer
from ..parsers.xer import xer_parser
import logging
from  django.conf import settings
import os
from django.core.cache import cache
from celery import shared_task
from ..data_extract.xer.table import construct_table
from rest_framework.parsers import MultiPartParser, FormParser

@shared_task
def task(saved_img_paths: list):
    pass
     #[ ###call parser:  takes saved_paths **remmber to [os.remove(path) for path in saved_paths]
        
        #-> pass to img_paths list to stability ai model for 3d


    
@api_view(['POST'])
def recon_controller(request):
    parser_classes = [MultiPartParser , FormParser]

    images = request.FILES.getlist("image")
    

    if images:
        saved_img_paths = []
        for img in images:
            if img.name.endswith(('.png','.jpg','.jpeg')):
                 tmp_dir = os.path.join(settings.BASE_DIR, 'tmp')
                 os.makedirs(tmp_dir, exist_ok=True)
                 logging.warning(f"Processing file: {img.name}")
                 imgfile_path = os.path.join(tmp_dir, img.name)
                 with open(imgfile_path, 'wb+') as destination:
                      for chunk in img.chunks():
                          destination.write(chunk)
                 saved_img_paths.append(imgfile_path)
            else:
              return Response({"error": "image file not valid must be png jpg or jpeg"}, status = status.HTTP_400_BAD_REQUEST)
    

        #->> call task function (would be celery function)
        res=  task(saved_img_paths)

    else:
        return Response({"error": "file not valid, upload valid image"}, status = status.HTTP_400_BAD_REQUEST)