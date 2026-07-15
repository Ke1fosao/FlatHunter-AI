from rest_framework import serializers


class TelegramAuthSerializer(serializers.Serializer):
    initData = serializers.CharField(max_length=16_384)
