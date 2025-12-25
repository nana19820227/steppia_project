from django.contrib import admin
from .models import Member, Job, Schedule, AIConsultTemplate, AIConsultLog, Applications, WorkLog

# 1. 会員情報を詳細に表示する設定
@admin.register(Member)  # 👈 これで登録されるので、下の register() は不要です
class MemberAdmin(admin.ModelAdmin):
    # 管理画面の一覧に「名前」「メール」「賃金日額」を表示
    list_display = ('last_name', 'first_name', 'email', 'daily_wage')
    # 検索窓でメールアドレスや名前を探せるようにする
    search_fields = ('last_name', 'first_name', 'email')

# 2. その他のモデルはシンプルに登録
admin.site.register(Job)
admin.site.register(Schedule)
admin.site.register(AIConsultTemplate)
admin.site.register(AIConsultLog)
admin.site.register(Applications)
admin.site.register(WorkLog)  