from rest_framework import serializers

class imageserializer(serializers.Serializer):
    images = serializers.ListField(child =  serializers.FileField() , allow_empty = False)
    file  =  serializers.FileField()
    def validate(self, attrs):
        img_value = attrs.get("images")
        file_value  = attrs.get("file")
        for file in img_value:
            if not file.name.endswith(('.jpg' , '.png' , '.jpeg' , '.heif')):
                raise serializers.ValidationError("Unsupported file type. Please upload a valid image file.")
        if not file_value.name.endswith(('.xer')):
                raise serializers.ValidationError("Unsupported file type. Please upload a valid .xer file file.")
        
        return attrs

