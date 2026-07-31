from django.contrib import admin

from .models import Batch, Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")

    # Deletion is closed here on purpose. The admin bypasses the guarded API path entirely:
    # BatchViewSet.perform_destroy restricts non-draft deletion to Super Admin and refuses a
    # batch that has issued certificates, and none of that runs from a change form. Worse, the
    # `delete_selected` bulk action would let someone tick fifty rows and cascade away their
    # entire academic history behind one confirmation page.
    #
    # Returning False here also removes `delete_selected` from the action list, because
    # Django gates that action on the "delete" permission (see the test that pins this).
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "course", "state", "start_date", "end_date")
    list_filter = ("state", "course")
    search_fields = ("code", "name")
    filter_horizontal = ("faculty",)

    # Deletion is closed here on purpose. The admin bypasses the guarded API path entirely:
    # BatchViewSet.perform_destroy restricts non-draft deletion to Super Admin and refuses a
    # batch that has issued certificates, and none of that runs from a change form. Worse, the
    # `delete_selected` bulk action would let someone tick fifty rows and cascade away their
    # entire academic history behind one confirmation page.
    #
    # Returning False here also removes `delete_selected` from the action list, because
    # Django gates that action on the "delete" permission (see the test that pins this).
    def has_delete_permission(self, request, obj=None):
        return False
