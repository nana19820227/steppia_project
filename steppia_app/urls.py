from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User  # 🆕 ユーザー作成用に追記
from django.http import HttpResponse         # 🆕 完了メッセージ表示用に追記
from . import views

# 🆕 緊急用：アクセスすると管理者ユーザーを作る関数
def make_user(request):
    username = 'okamuranana'
    password = 'admin2026'  # 👈 ログインに使いたいパスワードに書き換えてください
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, '', password)
        return HttpResponse(f"ユーザー '{username}' を作成しました！ログイン画面から試してください。")
    else:
        return HttpResponse(f"ユーザー '{username}' は既に存在します。")

urlpatterns = [
    # 🆕 緊急用URL（作業が終わったら後で消します）
    path('make-user-emergency/', make_user),
    
    # --- 1. メニュー画面（TOP） ---
    path('', views.top, name='menu'),
    
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