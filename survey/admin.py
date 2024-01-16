from django.contrib import admin
from .models import Survey
# Register your models here.

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['id','survey_id', 'collector_id', 'product']