from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("title", models.CharField(max_length=255)),
                ("file", models.FileField(upload_to="uploads/")),
                ("file_type", models.CharField(choices=[("pdf","PDF"),("audio","Audio"),("video","Video")], max_length=10)),
                ("file_size", models.PositiveIntegerField(help_text="Size in bytes")),
                ("status", models.CharField(choices=[("pending","Pending"),("processing","Processing"),("ready","Ready"),("failed","Failed")], default="pending", max_length=20)),
                ("summary", models.TextField(blank=True, default="")),
                ("transcript", models.TextField(blank=True, default="")),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                ("chroma_collection_id", models.CharField(blank=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="auth.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Timestamp",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("topic", models.CharField(max_length=255)),
                ("start_seconds", models.FloatField()),
                ("end_seconds", models.FloatField()),
                ("text_snippet", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="timestamps", to="api.document")),
            ],
            options={"ordering": ["start_seconds"]},
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("role", models.CharField(choices=[("user","User"),("assistant","Assistant")], max_length=10)),
                ("content", models.TextField()),
                ("source_pages", models.JSONField(blank=True, default=list)),
                ("source_timestamps", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="api.document")),
            ],
            options={"ordering": ["created_at"]},
        ),
    ]
