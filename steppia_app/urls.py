from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User
from django.http import HttpResponse
from . import views

# 🆕 緊急用：ユーザーを強制作成する関数（そのまま維持）
def make_user(request):
    username = 'okamuranana'
    password = 'admin2026'
    User.objects.filter(username=username).delete()
    User.objects.create_superuser(username, '', password)
    return HttpResponse(f"ユーザー '{username}' を【最強の管理者】として作成しました！")

urlpatterns = [
    # 救済用URL
    path('make-user-emergency/', make_user),
    
    # --- 1. メニュー画面（TOP） ---
    # 🆕 エラー防止：'top' と 'menu' どちらの名前で呼ばれても views.top を開くようにします
    path('', views.top, name='top'),
    path('menu/', views.top, name='menu'),
    
    # --- 2. 会員登録・求人関連 ---
    path('signup/', views.signup, name='signup'),
    path('signup/profile/', views.signup_profile, name='signup_profile'), 
    path('signup/confirm/', views.signup_confirm, name='signup_confirm'),
    path('signup/done/', views.signup_done, name='signup_done'),
    path('members/', views.member_list, name='member_list'),
    
    # --- 3. お仕事・応募機能 ---
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply_to_job, name='apply_to_job'),
    path('apply-done/', views.apply_done, name='apply_done'),
    
    # --- 4. お仕事ログ ---
    path('work-tracker/', views.work_tracker, name='work_tracker'),
    path('work-tracker/edit/<int:pk>/', views.edit_work_log, name='edit_work_log'),
    path('work-tracker/delete/<int:pk>/', views.delete_work_log, name='delete_work_log'),
    
    # --- 5. 相談室・マイページ ---
    path('ai-consult/', views.ai_consult, name='ai_consult'),
    path('ai-history/', views.ai_history, name='ai_history'),
    path('mypage/', views.mypage, name='mypage'),
    
    # --- 6. スケジュール・コンサル相談 ---
    path('schedule/', views.schedule, name='schedule'),
    path('consult/', views.consult_top, name='consult_top'),
    path('consult/setting/', views.consult_setting, name='consult_setting'),
    path('consult/setting/done/', views.consult_setting_done, name='consult_setting_done'),
    path('consult/reservation/', views.consult_reservation, name='consult_reservation'),
    path('consult/confirm/', views.consult_confirm, name='consult_confirm'),
    path('consult/done/', views.consult_reservation_done, name='consult_reservation_done'),
    
    # --- 7. 認証・進捗管理 ---
    path('login/', LoginView.as_view(template_name='steppia_app/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('progress/', views.progress, name='progress'),
    path('congrats/', views.congrats, name='congrats'),
    path('congrats-map/', views.congrats_map, name='congrats_map'),

    # --- 8. ルーレット ---
    path('roulette/', views.roulette, name='roulette'),
    path('roulette/result/<str:item>/', views.roulette_result, name='roulette_result'),
    path('roulette-lost/', views.roulette_lost, name='roulette_lost'),
]