import uuid
from unittest.mock import patch, MagicMock
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from api.models import Document, ChatMessage, Timestamp


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def auth_client(client, user):
    response = client.post(
        "/api/auth/login/",
        {"username": "testuser", "password": "testpass123"},
        format="json",
    )
    token = response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def pdf_document(db, user):
    return Document.objects.create(
        user=user,
        title="Test PDF",
        file="uploads/test.pdf",
        file_type="pdf",
        file_size=1024,
        status="ready",
        summary="A test document summary.",
        chroma_collection_id="doc_testcollection",
    )


@pytest.fixture
def audio_document(db, user):
    return Document.objects.create(
        user=user,
        title="Test Audio",
        file="uploads/test.mp3",
        file_type="audio",
        file_size=2048,
        status="ready",
        summary="An audio summary.",
        transcript="Hello world. This is a test transcript.",
        duration_seconds=60.0,
        chroma_collection_id="doc_audiocollection",
    )


# ─── Auth Tests ──────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client, db):
        response = client.post(
            "/api/auth/register/",
            {"username": "newuser", "email": "new@example.com", "password": "securepass"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    def test_register_duplicate_username(self, client, user):
        response = client.post(
            "/api/auth/register/",
            {"username": "testuser", "password": "anotherpass"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_short_password(self, client, db):
        response = client.post(
            "/api/auth/register/",
            {"username": "user2", "password": "123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAuth:
    def test_login_success(self, client, user):
        response = client.post(
            "/api/auth/login/",
            {"username": "testuser", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_wrong_password(self, client, user):
        response = client.post(
            "/api/auth/login/",
            {"username": "testuser", "password": "wrong"},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self, auth_client, user):
        response = auth_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"

    def test_me_unauthenticated(self, client):
        response = client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Document Tests ──────────────────────────────────────────────────────────

class TestDocumentList:
    def test_list_empty(self, auth_client):
        response = auth_client.get("/api/documents/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_list_returns_user_docs_only(self, auth_client, pdf_document, db):
        other_user = User.objects.create_user(username="other", password="pass")
        Document.objects.create(
            user=other_user, title="Other Doc", file="uploads/x.pdf",
            file_type="pdf", file_size=100, status="ready",
        )
        response = auth_client.get("/api/documents/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Test PDF"

    @patch("api.views.process_document")
    @patch("api.views.threading.Thread")
    def test_upload_pdf(self, mock_thread, mock_process, auth_client, db):
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        pdf_content = b"%PDF-1.4 test content"
        f = SimpleUploadedFile("doc.pdf", pdf_content, content_type="application/pdf")
        response = auth_client.post(
            "/api/documents/",
            {"title": "My PDF", "file": f},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["file_type"] == "pdf"
        assert response.data["status"] == "pending"

    def test_upload_unsupported_type(self, auth_client):
        f = SimpleUploadedFile("doc.exe", b"binary", content_type="application/octet-stream")
        response = auth_client.post(
            "/api/documents/",
            {"title": "Bad", "file": f},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_requires_auth(self, client):
        f = SimpleUploadedFile("doc.pdf", b"%PDF", content_type="application/pdf")
        response = client.post("/api/documents/", {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDocumentDetail:
    def test_get_document(self, auth_client, pdf_document):
        response = auth_client.get(f"/api/documents/{pdf_document.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Test PDF"

    def test_get_other_user_document(self, auth_client, db):
        other = User.objects.create_user(username="other2", password="pass")
        other_doc = Document.objects.create(
            user=other, title="Private", file="uploads/x.pdf",
            file_type="pdf", file_size=100, status="ready",
        )
        response = auth_client.get(f"/api/documents/{other_doc.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_document(self, auth_client, pdf_document):
        with patch("api.views.get_chroma_client") as mock_chroma:
            mock_chroma.return_value.delete_collection = MagicMock()
            with patch.object(pdf_document.file, "delete"):
                response = auth_client.delete(f"/api/documents/{pdf_document.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT


# ─── Ask / Chat Tests ────────────────────────────────────────────────────────

class TestAsk:
    @patch("api.views.query_document")
    @patch("api.views.generate_answer")
    def test_ask_success(self, mock_generate, mock_query, auth_client, pdf_document):
        mock_query.return_value = [{"text": "Some context", "metadata": {"page": 1}}]
        mock_generate.return_value = {"answer": "The answer is 42.", "sources": [{"page": 1}]}

        response = auth_client.post(
            f"/api/documents/{pdf_document.id}/ask/",
            {"question": "What is the answer?"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["content"] == "The answer is 42."
        assert response.data["role"] == "assistant"
        assert ChatMessage.objects.filter(document=pdf_document).count() == 2

    def test_ask_document_not_ready(self, auth_client, db, user):
        doc = Document.objects.create(
            user=user, title="Proc", file="uploads/x.pdf",
            file_type="pdf", file_size=100, status="processing",
        )
        response = auth_client.post(
            f"/api/documents/{doc.id}/ask/",
            {"question": "Hello?"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_ask_empty_question(self, auth_client, pdf_document):
        response = auth_client.post(
            f"/api/documents/{pdf_document.id}/ask/",
            {"question": ""},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chat_history(self, auth_client, pdf_document):
        ChatMessage.objects.create(document=pdf_document, role="user", content="Q1")
        ChatMessage.objects.create(document=pdf_document, role="assistant", content="A1")
        response = auth_client.get(f"/api/documents/{pdf_document.id}/chat/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_clear_chat(self, auth_client, pdf_document):
        ChatMessage.objects.create(document=pdf_document, role="user", content="Q")
        response = auth_client.delete(f"/api/documents/{pdf_document.id}/chat/")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert ChatMessage.objects.filter(document=pdf_document).count() == 0


# ─── Summary Tests ───────────────────────────────────────────────────────────

class TestSummary:
    def test_get_summary(self, auth_client, pdf_document):
        response = auth_client.get(f"/api/documents/{pdf_document.id}/summary/")
        assert response.status_code == status.HTTP_200_OK
        assert "summary" in response.data
        assert response.data["status"] == "ready"


# ─── Timestamp Tests ─────────────────────────────────────────────────────────

class TestTimestamps:
    def test_timestamp_on_pdf_fails(self, auth_client, pdf_document):
        response = auth_client.get(
            f"/api/documents/{pdf_document.id}/timestamps/?topic=intro"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.views.extract_timestamps_for_topic")
    def test_timestamp_on_audio(self, mock_extract, auth_client, audio_document):
        mock_extract.return_value = [
            {"start": 0.0, "end": 5.0, "text": "Hello world.", "relevance_note": "intro"}
        ]
        response = auth_client.get(
            f"/api/documents/{audio_document.id}/timestamps/?topic=intro"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_timestamps_no_topic_returns_saved(self, auth_client, audio_document):
        Timestamp.objects.create(
            document=audio_document,
            topic="intro",
            start_seconds=0.0,
            end_seconds=5.0,
            text_snippet="Hello",
        )
        response = auth_client.get(f"/api/documents/{audio_document.id}/timestamps/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


# ─── Service Unit Tests ──────────────────────────────────────────────────────

class TestDocumentProcessor:
    def test_detect_file_type_pdf(self):
        from api.services.document_processor import detect_file_type
        assert detect_file_type("report.pdf") == "pdf"

    def test_detect_file_type_audio(self):
        from api.services.document_processor import detect_file_type
        assert detect_file_type("recording.mp3") == "audio"
        assert detect_file_type("voice.wav") == "audio"

    def test_detect_file_type_video(self):
        from api.services.document_processor import detect_file_type
        assert detect_file_type("lecture.mp4") == "video"

    def test_detect_file_type_unknown(self):
        from api.services.document_processor import detect_file_type
        assert detect_file_type("file.exe") == "unknown"

    def test_chunk_text_basic(self):
        from api.services.document_processor import chunk_text
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)

    def test_chunk_text_short(self):
        from api.services.document_processor import chunk_text
        chunks = chunk_text("hello world", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_chunk_text_overlap(self):
        from api.services.document_processor import chunk_text
        words = [f"w{i}" for i in range(200)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=50, overlap=10)
        # With overlap, adjacent chunks should share some words
        assert len(chunks) >= 4
