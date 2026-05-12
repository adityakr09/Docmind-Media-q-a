import uuid
from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    FILE_TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("audio", "Audio"),
        ("video", "Video"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    summary = models.TextField(blank=True, default="")
    transcript = models.TextField(blank=True, default="")
    duration_seconds = models.FloatField(null=True, blank=True)
    chroma_collection_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.file_type})"


class Timestamp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="timestamps"
    )
    topic = models.CharField(max_length=255)
    start_seconds = models.FloatField()
    end_seconds = models.FloatField()
    text_snippet = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_seconds"]

    def __str__(self):
        return f"{self.topic} @ {self.start_seconds}s"


class ChatMessage(models.Model):
    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    source_pages = models.JSONField(default=list, blank=True)
    source_timestamps = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
