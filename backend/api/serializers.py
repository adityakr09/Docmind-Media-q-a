from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, Timestamp, ChatMessage


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class TimestampSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timestamp
        fields = ["id", "topic", "start_seconds", "end_seconds", "text_snippet"]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "source_pages", "source_timestamps", "created_at"]


class DocumentSerializer(serializers.ModelSerializer):
    timestamps = TimestampSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "file_type", "file_size", "status",
            "summary", "duration_seconds", "timestamps",
            "message_count", "created_at", "updated_at",
        ]

    def get_message_count(self, obj):
        return obj.messages.count()


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["title", "file"]

    def validate_file(self, value):
        allowed = [".pdf", ".mp3", ".mp4", ".wav", ".m4a", ".webm"]
        ext = "." + value.name.split(".")[-1].lower()
        if ext not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(allowed)}"
            )
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB.")
        return value


class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000)
