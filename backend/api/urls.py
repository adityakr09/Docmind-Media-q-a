from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/me/", views.MeView.as_view(), name="me"),

    # Documents
    path("documents/", views.DocumentListView.as_view(), name="document-list"),
    path("documents/<uuid:doc_id>/", views.DocumentDetailView.as_view(), name="document-detail"),
    path("documents/<uuid:doc_id>/summary/", views.summary_view, name="document-summary"),

    # Chat
    path("documents/<uuid:doc_id>/ask/", views.AskView.as_view(), name="ask"),
    path("documents/<uuid:doc_id>/chat/", views.ChatHistoryView.as_view(), name="chat-history"),

    # Timestamps
    path("documents/<uuid:doc_id>/timestamps/", views.TimestampSearchView.as_view(), name="timestamps"),
]
