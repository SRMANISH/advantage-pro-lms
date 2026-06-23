from django.contrib import admin

from .models import Batch, Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "course", "state", "start_date", "end_date")
    list_filter = ("state", "course")
    search_fields = ("code", "name")
    filter_horizontal = ("faculty",)
