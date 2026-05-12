from django.contrib import admin
from .models import Document, Timestamp, ChatMessage


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "file_type", "status", "created_at"]
    list_filter = ["file_type", "status"]
    search_fields = ["title", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at", "chroma_collection_id"]


@admin.register(Timestamp)
class TimestampAdmin(admin.ModelAdmin):
    list_display = ["topic", "document", "start_seconds", "end_seconds"]
    list_filter = ["document__file_type"]
    search_fields = ["topic"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["role", "document", "content_preview", "created_at"]
    list_filter = ["role"]

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Content"
