from rest_framework import serializers


class docandcontext(serializers.Serializer):
    files = serializers.ListField(child =  serializers.FileField() , allow_empty = False)
    prompt =  serializers.CharField()  #containing project constraints and priorities

    def validate(self, attrs):
        value = attrs.get("files")
        for file in value:
            if not file.name.endswith(('.xer')):
                raise serializers.ValidationError("Unsupported file type. Please upload a valid schedule file.")
        return attrs