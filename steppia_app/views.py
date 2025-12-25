from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
import pytz

# すべてのモデルをインポート
from .models import Schedule, Member, Job, AIConsultTemplate, AIConsultLog, Applications, WorkLog, Coupon

# --- 1. 基本・メニュー ---
def top(request):
    """メインメニュー画面を表示する"""
    return render(request, 'steppia_app/top.html')

# --- 2. 会員登録（ログイン用アカウント作成） ---
def signup(request):
    """ステップ1: ログイン用のユーザーアカウント(User)を作成する"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # アカウント作成後、自動でログイン状態にする
            return redirect('signup_profile') 
    else:
        form = UserCreationForm()
    return render(request, 'steppia_app/signup.html', {'form': form})

@login_required
def signup_profile(request):
    """ステップ2: 会員詳細情報（Member）の入力画面"""
    return render(request, 'steppia_app/signup_profile.html')

def signup_confirm(request):
    """会員登録確認画面"""
    context = {
        'last_name': request.GET.get('last_name'),
        'first_name': request.GET.get('first_name'),
        'last_name_kana': request.GET.get('last_name_kana'),
        'first_name_kana': request.GET.get('first_name_kana'),
        'address': request.GET.get('address'),
        'phone': request.GET.get('phone'),
        'email': request.GET.get('email'),
    }
    return render(request, 'steppia_app/signup_confirm.html', context)

@login_required
def signup_done(request):
    """会員登録完了：新しいMemberを作成しログインユーザーと紐付け"""
    if request.method == 'POST':
        Member.objects.create(
            user=request.user,
            last_name=request.POST.get('last_name'),
            first_name=request.POST.get('first_name'),
            last_name_kana=request.POST.get('last_name_kana'),
            first_name_kana=request.POST.get('first_name_kana'),
            address=request.POST.get('address'),
            phone=request.POST.get('phone'),
            email=request.POST.get('email')
        )
    return render(request, 'steppia_app/signup_done.html')

@login_required
def member_list(request):
    """管理者用：会員一覧画面"""
    members = Member.objects.all()
    return render(request, 'steppia_app/member_list.html', {'members': members})

# --- 3. 求人・応募機能 ---
def job_list(request):
    """求人一覧画面"""
    jobs = Job.objects.all()
    return render(request, 'steppia_app/job_list.html', {'jobs': jobs})

def job_detail(request, pk):
    """求人詳細画面"""
    job = get_object_or_404(Job, pk=pk)
    return render(request, 'steppia_app/job_detail.html', {'job': job})

@login_required
def apply_to_job(request, pk):
    """求人への応募処理"""
    job = get_object_or_404(Job, pk=pk)
    Applications.objects.get_or_create(user=request.user, job=job)
    return redirect('apply_done')

def apply_done(request):
    """応募完了画面"""
    consultant_name = request.session.get('selected_consultant', '担当コンサルタント')
    return render(request, 'steppia_app/apply_done.html', {'consultant_name': consultant_name})

# --- 4. お仕事ログ ---
@login_required
def work_tracker(request):
    """就労状況の記録と制限チェック"""
    if request.method == 'POST':
        date = request.POST.get('date')
        hours = request.POST.get('hours')
        amount = request.POST.get('amount')
        company = request.POST.get('company')
        first_job = Job.objects.first()
        if date and amount:
            WorkLog.objects.create(
                user=request.user,
                job=first_job, 
                company_name=company if company else "（未入力）",
                date=date,
                hours=hours if hours else 0,
                earnings=int(amount)
            )
            return redirect('work_tracker')

    member = Member.objects.filter(user=request.user).first()
    daily_wage = member.daily_wage if member else 0
    limit_80 = int(daily_wage * 0.8)
    logs = WorkLog.objects.filter(user=request.user).order_by('-date')
    
    for log in logs:
        log.is_over_limit = (log.earnings > limit_80) if limit_80 > 0 else False
    
    context = {
        'member': member,
        'logs': logs, 
        'total_hours': sum(log.hours for log in logs) if logs else 0, 
        'total_earnings': sum(log.earnings for log in logs) if logs else 0, 
        'limit_80': limit_80
    }
    return render(request, 'steppia_app/work_tracker.html', context)

# --- 5. AI相談室 ---
def ai_consult(request):
    """FAQデータに基づいたAI相談回答"""
    ai_answer = ""
    user_q = ""
    
    # ... (FAQ_DATAは長いので省略しますが、既存のものをそのまま保持してください) ...
    FAQ_DATA = {
        "40代": "40代は経験の宝庫です。スキルだけでなく、これまでの柔軟な対応力をアピールしましょう。",
        "未経験": "異業種でも、共通する「調整力や管理能力（ポータブルスキル）」を言語化するのが鍵です。",
        # (以下、お手元のコードのFAQ_DATAをそのまま残してください)
    }
        
    if request.method == 'POST':
        user_q = (request.POST.get('user_input') or request.POST.get('user_text', '')).strip()
        if user_q:
            user_q_clean = user_q.replace('。','').replace('？','').replace('?','')
            all_templates = AIConsultTemplate.objects.all()
            template_match = None
            for t in all_templates:
                t_q_clean = t.question.replace('。','').replace('？','').replace('?','').strip()
                if t_q_clean and (t_q_clean in user_q_clean or user_q_clean in t_q_clean):
                    template_match = t
                    break
            
            if template_match:
                ai_answer = template_match.answer
            else:
                found_answer = None
                for keyword, answer in FAQ_DATA.items():
                    if keyword in user_q:
                        found_answer = answer
                        break
                ai_answer = found_answer if found_answer else "担当コンサルタントに直接ご相談してみてくださいね。"

            AIConsultLog.objects.create(user_question=user_q, ai_response=ai_answer)

    return render(request, 'steppia_app/ai_consult.html', {'ai_answer': ai_answer, 'user_q': user_q})

def ai_history(request):
    return redirect('mypage')

# --- 6. マイページ ---
@login_required
def mypage(request):
    """ユーザーに関連するすべての情報を集約表示"""
    logs = AIConsultLog.objects.all().order_by('-created_at')
    mypage_schedules = Schedule.objects.filter(detail__contains='コンサル予約').order_by('-date', '-time')
    user_applications = Applications.objects.filter(user=request.user).order_by('-applied_at')
    consultant_name = request.session.get('selected_consultant', '未設定')
    coupons = Coupon.objects.filter(user=request.user, is_used=False).order_by('-won_at')
    return render(request, 'steppia_app/mypage.html', {
        'logs': logs, 'mypage_schedules': mypage_schedules, 
        'applications': user_applications, 'consultant_name': consultant_name, 
        'coupons': coupons
    })

# --- 7. 進捗管理（冒険マップ） ---
@login_required
def progress(request):
    """【500エラー修正版】データの有無に関わらず安全に表示する"""
    # ユーザーの状態をDBから確認
    is_signed_up = Member.objects.filter(user=request.user).exists()
    has_logs = AIConsultLog.objects.filter(user_question__isnull=False).exists()
    has_res = Schedule.objects.filter(detail__contains='コンサル予約').exists()
    has_applied = Applications.objects.filter(user=request.user).exists()
    
    status = {
        'step1': is_signed_up, 
        'step2': request.session.get('step2', False), 
        'step3': request.session.get('step3', False), 
        'step4': has_applied, 
        'step5': has_logs, 
        'step6': has_res
    }
    
    current_pos = 1
    for i in range(1, 7):
        if status.get(f'step{i}'): current_pos = i
    
    # 🆕 携帯でもPCでも、作成済みの 'progress.html' を使用するように固定
    # これにより progress_mobile.html がないことによる500エラーを防ぎます
    return render(request, 'steppia_app/progress.html', {
        'status': status, 
        'current_pos': current_pos
    })

# --- 8. コンサル予約・スケジュール ---
def consult_top(request): 
    return render(request, 'steppia_app/consult_top.html')

def consult_setting(request):
    if request.method == 'POST':
        request.session['selected_consultant'] = request.POST.get('consultant_name')
        return redirect('consult_setting_done')
    return render(request, 'steppia_app/consult_setting.html')

def consult_reservation(request): 
    return render(request, 'steppia_app/consult_reservation.html')

def consult_confirm(request):
    return render(request, 'steppia_app/consult_confirm.html', {
        'date': request.POST.get('date'), 
        'time': request.POST.get('time'), 
        'consultant': request.POST.get('consultant')
    })

def consult_setting_done(request): 
    return render(request, 'steppia_app/consult_setting_done.html')

def consult_reservation_done(request):
    if request.method == 'POST':
        Schedule.objects.create(
            date=request.POST.get('date'), 
            time=request.POST.get('time'), 
            detail=f"{request.POST.get('consultant')} コンサル予約"
        )
        coupon_id = request.POST.get('coupon_id')
        if coupon_id:
            coupon = Coupon.objects.filter(id=coupon_id, user=request.user).first()
            if coupon:
                coupon.is_used = True
                coupon.save()
    return render(request, 'steppia_app/consult_reservation_done.html')

def schedule(request):
    if request.method == 'POST':
        Schedule.objects.create(
            date=request.POST.get('date'), 
            time=request.POST.get('time'), 
            detail=request.POST.get('detail')
        )
    return render(request, 'steppia_app/schedule.html', {'schedules': Schedule.objects.all().order_by('-date', '-time')})

# --- 9. 🎁 ルーレット関連 ---
@login_required
def roulette(request):
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = timezone.now().astimezone(jst)
    today_jst = now_jst.date()

    member = Member.objects.filter(user=request.user).first()
    can_spin = True
    if member and member.last_roulette_date == today_jst:
        can_spin = False
    
    return render(request, 'steppia_app/roulette.html', {'can_spin': can_spin})

@login_required
def roulette_result(request, item):
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = timezone.now().astimezone(jst)
    today_jst = now_jst.date()

    member = Member.objects.filter(user=request.user).first()
    if member:
        member.last_roulette_date = today_jst
        member.save()

    is_win = "賞" in item or "面談" in item
    if is_win:
        Coupon.objects.get_or_create(user=request.user, prize_name=item, is_used=False)
    
    return render(request, 'steppia_app/roulette_result.html', {'item': item, 'is_win': is_win})

@login_required
def congrats(request):
    prize = request.GET.get('prize', '豪華賞品')
    return render(request, 'steppia_app/congrats.html', {'prize': prize})

def roulette_lost(request):
    return render(request, 'steppia_app/roulette_lost.html')

# --- 10. 🌸 お祝い・マップ関連 ---
@login_required
def congrats_map(request):
    return render(request, 'steppia_app/congrats_map.html')