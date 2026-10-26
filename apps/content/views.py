from django.views.generic import TemplateView

from .models import StaffMember


class ContactsView(TemplateView):
    """Страница контактов: карточки руководства штаба и офис."""

    template_name = "content/contacts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["staff_members"] = StaffMember.objects.filter(is_active=True).select_related("user")
        return context
