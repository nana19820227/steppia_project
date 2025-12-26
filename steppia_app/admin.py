from django.contrib import admin
# Applications を Application (単数形) に修正
from .models import Member, Job, Schedule, AIConsultTemplate, AIConsultLog, Application, WorkLog, Coupon

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'email', 'daily_wage', 'last_roulette_date')
    search_fields = ('last_name', 'first_name', 'email')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'job', 'current_step', 'status', 'applied_at')

admin.site.register(Job)
admin.site.register(Schedule)
admin.site.register(AIConsultTemplate)
admin.site.register(AIConsultLog)
admin.site.register(WorkLog)
admin.site.register(Coupon)