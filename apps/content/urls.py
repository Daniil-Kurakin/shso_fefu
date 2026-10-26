from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("contacts/", views.ContactsView.as_view(), name="contacts"),
    # База знаний
    path("knowledge/", views.KnowledgeIndexView.as_view(), name="knowledge_index"),
    path("knowledge/create/", views.KnowledgeArticleCreateView.as_view(), name="knowledge_create"),
    path(
        "knowledge/<str:category_slug>/<str:slug>/edit/",
        views.KnowledgeArticleUpdateView.as_view(),
        name="knowledge_edit",
    ),
    path(
        "knowledge/<str:category_slug>/",
        views.KnowledgeCategoryView.as_view(),
        name="knowledge_category",
    ),
    path(
        "knowledge/<str:category_slug>/<str:slug>/",
        views.KnowledgeDetailView.as_view(),
        name="knowledge_detail",
    ),
    # FAQ и Глоссарий
    path("faq/", views.FAQListView.as_view(), name="faq"),
    path("faq/create/", views.FAQItemCreateView.as_view(), name="faq_create"),
    path("glossary/", views.GlossaryListView.as_view(), name="glossary"),
    path("glossary/create/", views.GlossaryTermCreateView.as_view(), name="glossary_create"),
    # Правовые документы (152-ФЗ, 149-ФЗ)
    path("privacy/", views.PrivacyPolicyView.as_view(), name="privacy"),
    path("terms/", views.TermsOfServiceView.as_view(), name="terms"),
]
