import threading
import logging

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Timestamp, ChatMessage
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    TimestampSerializer,
    ChatMessageSerializer,
    AskQuestionSerializer,
)
from .services.document_processor import (
    process_document,
    query_document,
    generate_answer,
    extract_timestamps_for_topic,
    detect_file_type,
)

logger = logging.getLogger(__name__)


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ─── Documents ───────────────────────────────────────────────────────────────

class DocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = Document.objects.filter(user=request.user)
        serializer = DocumentSerializer(docs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = serializer.validated_data["file"]
        title = serializer.validated_data.get("title") or file.name
        file_type = detect_file_type(file.name)

        if file_type == "unknown":
            return Response(
                {"error": "Unsupported file type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = Document.objects.create(
            user=request.user,
            title=title,
            file=file,
            file_type=file_type,
            file_size=file.size,
            status="pending",
        )

        # Process in background thread so upload returns immediately
        thread = threading.Thread(target=process_document, args=(doc,), daemon=True)
        thread.start()

        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)
        return Response(DocumentSerializer(doc).data)

    def delete(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)
        # Remove ChromaDB collection
        if doc.chroma_collection_id:
            try:
                from .services.document_processor import get_chroma_client
                client = get_chroma_client()
                client.delete_collection(doc.chroma_collection_id)
            except Exception:
                pass
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Chat ────────────────────────────────────────────────────────────────────

class AskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)

        if doc.status != "ready":
            return Response(
                {"error": f"Document is {doc.status}. Please wait until processing is complete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AskQuestionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question = serializer.validated_data["question"]

        # Save user message
        ChatMessage.objects.create(
            document=doc,
            role="user",
            content=question,
        )

        try:
            context_chunks = query_document(doc.chroma_collection_id, question)
            result = generate_answer(question, context_chunks, doc.file_type)

            source_pages = [
                s.get("page") for s in result["sources"] if s.get("page")
            ]
            source_timestamps = [
                {"start": s.get("start"), "end": s.get("end")}
                for s in result["sources"]
                if s.get("start") is not None
            ]

            ai_message = ChatMessage.objects.create(
                document=doc,
                role="assistant",
                content=result["answer"],
                source_pages=source_pages,
                source_timestamps=source_timestamps,
            )

            return Response(ChatMessageSerializer(ai_message).data)

        except Exception as e:
            logger.error(f"Ask error for doc {doc_id}: {e}")
            return Response(
                {"error": "Failed to generate answer. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)
        messages = doc.messages.all()
        return Response(ChatMessageSerializer(messages, many=True).data)

    def delete(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)
        doc.messages.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Timestamps ──────────────────────────────────────────────────────────────

class TimestampSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        doc = get_object_or_404(Document, id=doc_id, user=request.user)
        topic = request.query_params.get("topic", "").strip()

        if doc.file_type not in ("audio", "video"):
            return Response(
                {"error": "Timestamp search is only available for audio/video files."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if doc.status != "ready":
            return Response(
                {"error": "Document is still processing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Return stored timestamps if no topic given
        if not topic:
            saved = doc.timestamps.all()
            return Response(TimestampSerializer(saved, many=True).data)

        # Extract from transcript using LLM
        import json
        try:
            segments = []
            if doc.transcript:
                from .services.document_processor import get_openai_client
                # Rebuild segments from chroma or use transcript lines
                lines = [l.strip() for l in doc.transcript.split(".") if l.strip()]
                for i, line in enumerate(lines):
                    segments.append({
                        "start": i * 5.0,
                        "end": (i + 1) * 5.0,
                        "text": line,
                    })

            results = extract_timestamps_for_topic(segments, topic)

            # Persist them
            for r in results:
                Timestamp.objects.get_or_create(
                    document=doc,
                    topic=topic,
                    start_seconds=r.get("start", 0),
                    defaults={
                        "end_seconds": r.get("end", 0),
                        "text_snippet": r.get("text", ""),
                    },
                )

            return Response(results)

        except Exception as e:
            logger.error(f"Timestamp error for doc {doc_id}: {e}")
            return Response(
                {"error": "Failed to extract timestamps."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ─── Summary ─────────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_view(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id, user=request.user)
    return Response({"summary": doc.summary, "status": doc.status})
