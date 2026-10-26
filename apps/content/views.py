from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView

from .models import (
    FAQCategory,
    FAQItem,
    GlossaryTerm,
    KnowledgeArticle,
    KnowledgeCategory,
    StaffMember,
)


class ContactsView(TemplateView):
    """Страница контактов: карточки руководства штаба и офис."""

    template_name = "content/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["staff_members"] = StaffMember.objects.filter(is_active=True).select_related("user")
        return context


class KnowledgeIndexView(TemplateView):
    """Главная страница базы знаний: категории, поиск и закреплённые статьи."""

    template_name = "content/knowledge_index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()

        context["categories"] = KnowledgeCategory.objects.prefetch_related("articles")
        context["q"] = q

        if q:
            context["search_results"] = (
                KnowledgeArticle.objects.filter(is_published=True)
                .filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q))
                .select_related("category")
            )
        else:
            context["search_results"] = None
            context["pinned_articles"] = KnowledgeArticle.objects.filter(
                is_published=True, pinned=True
            ).select_related("category")[:6]

        return context


class KnowledgeCategoryView(ListView):
    """Статьи внутри одной категории базы знаний."""

    model = KnowledgeArticle
    template_name = "content/knowledge_category.html"
    context_object_name = "articles"

    def get_queryset(self):
        self.category = get_object_or_404(KnowledgeCategory, slug=self.kwargs["category_slug"])
        qs = KnowledgeArticle.objects.filter(category=self.category, is_published=True)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        context["q"] = self.request.GET.get("q", "")
        return context


class KnowledgeDetailView(DetailView):
    """Чтение статьи базы знаний с подсчётом просмотров."""

    model = KnowledgeArticle
    template_name = "content/knowledge_detail.html"
    context_object_name = "article"

    def get_object(self, queryset=None):
        article = get_object_or_404(
            KnowledgeArticle.objects.select_related("category"),
            category__slug=self.kwargs["category_slug"],
            slug=self.kwargs["slug"],
            is_published=True,
        )

        # Защита от накрутки просмотров в текущей сессии
        session_key = "viewed_articles"
        viewed = self.request.session.get(session_key, [])
        if article.pk not in viewed:
            KnowledgeArticle.objects.filter(pk=article.pk).update(views_count=F("views_count") + 1)
            article.views_count += 1
            viewed.append(article.pk)
            self.request.session[session_key] = viewed

        return article

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.object.category
        context["related_articles"] = KnowledgeArticle.objects.filter(
            category=self.object.category, is_published=True
        ).exclude(pk=self.object.pk)[:5]
        return context


class FAQListView(ListView):
    """Часто задаваемые вопросы (FAQ) с фильтрацией по категориям и поиском."""

    model = FAQItem
    template_name = "content/faq.html"
    context_object_name = "faq_items"

    def get_queryset(self):
        qs = FAQItem.objects.filter(is_published=True).select_related("category")
        cat_slug = self.request.GET.get("category", "").strip()
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(question__icontains=q) | Q(answer__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = FAQCategory.objects.all()
        context["current_category"] = self.request.GET.get("category", "")
        context["q"] = self.request.GET.get("q", "")
        return context


class GlossaryListView(ListView):
    """Глоссарий отрядных терминов с алфавитным указателем и поиском."""

    model = GlossaryTerm
    template_name = "content/glossary.html"
    context_object_name = "terms"

    def get_queryset(self):
        qs = GlossaryTerm.objects.all()
        letter = self.request.GET.get("letter", "").strip().upper()
        if letter:
            qs = qs.filter(letter=letter)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(term__icontains=q) | Q(definition__icontains=q) | Q(synonyms__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем список всех доступных букв в базе
        letters = list(
            GlossaryTerm.objects.values_list("letter", flat=True).distinct().order_by("letter")
        )
        context["letters"] = letters
        context["current_letter"] = self.request.GET.get("letter", "").strip().upper()
        context["q"] = self.request.GET.get("q", "")
        return context


class PrivacyPolicyView(TemplateView):
    """Политика в отношении обработки персональных данных (152-ФЗ ст. 18.1)."""

    template_name = "content/privacy_policy.html"


class TermsOfServiceView(TemplateView):
    """Пользовательское соглашение и правила пользования сайтом."""

    template_name = "content/terms_of_service.html"
