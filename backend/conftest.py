import django
from django.conf import settings


def pytest_configure():
    settings.DATABASES["default"]["NAME"] = "mediaqa_test"
    settings.OPENAI_API_KEY = "test-key-not-real"
    settings.CHROMA_PERSIST_DIR = "/tmp/chroma_test"
