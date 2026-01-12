from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
from django.views.decorators.cache import never_cache
import random  # 🆕 ここで1回だけ宣言すればOK
import pytz

# すべてのモデルをインポート
from .models import (
    Schedule, Member, Job, AIConsultTemplate, 
    AIConsultLog, Application, WorkLog, Coupon
)

# --- 1. 基本・メニュー ---
def top(request):
    """トップ画面"""
    return render(request, 'steppia_app/top.html')

# --- 2. 会員登録フロー ---
def signup(request):
    """ステップ1: アカウント作成"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('signup_profile') 
    else:
        form = UserCreationForm()
    return render(request, 'steppia_app/signup.html', {'form': form})

@login_required
def signup_profile(request):
    """ステップ2: 詳細入力"""
    return render(request, 'steppia_app/signup_profile.html')

def signup_confirm(request):
    """登録内容確認"""
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
    """完了画面：自動作成されたMemberを更新"""
    if request.method == 'POST':
        member = request.user.profile
        member.last_name = request.POST.get('last_name')
        member.first_name = request.POST.get('first_name')
        member.last_name_kana = request.POST.get('last_name_kana')
        member.first_name_kana = request.POST.get('first_name_kana')
        member.address = request.POST.get('address')
        member.phone = request.POST.get('phone')
        member.email = request.POST.get('email')
        member.save()
    return render(request, 'steppia_app/signup_done.html')

@login_required
def member_list(request):
    members = Member.objects.all()
    return render(request, 'steppia_app/member_list.html', {'members': members})

# --- 3. 求人・応募機能 ---
def job_list(request):
    jobs = Job.objects.all()
    return render(request, 'steppia_app/job_list.html', {'jobs': jobs})

def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    return render(request, 'steppia_app/job_detail.html', {'job': job})

@login_required
def apply_to_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    Application.objects.get_or_create(user=request.user, job=job)
    return redirect('apply_done')

def apply_done(request):
    """応募完了画面：保存された担当者名を優先表示"""
    member = request.user.profile if request.user.is_authenticated else None
    consultant_name = member.assigned_consultant if member and member.assigned_consultant else request.session.get('selected_consultant', '担当コンサルタント')
    return render(request, 'steppia_app/apply_done.html', {'consultant_name': consultant_name})

# --- 4. お仕事ログ ---
@login_required
def work_tracker(request):
    show_warning = False
    if request.method == 'POST':
        date_str = request.POST.get('date')
        hours = request.POST.get('hours')
        amount = request.POST.get('amount')
        company = request.POST.get('company')
        if date_str and amount:
            WorkLog.objects.create(
                user=request.user,
                company_name=company if company else "（未入力）",
                date=date_str,
                hours=float(hours) if hours else 0,
                earnings=int(amount)
            )
            stats = WorkLog.objects.filter(user=request.user, date=date_str).aggregate(
                total_pay=Sum('earnings'), total_hrs=Sum('hours')
            )
            if (stats['total_pay'] or 0) >= 4000 or (stats['total_hrs'] or 0) > 2:
                show_warning = True

    logs = WorkLog.objects.filter(user=request.user).order_by('-date')
    context = {
        'logs': logs, 'show_warning': show_warning,
        'total_hours': sum(log.hours for log in logs), 
        'total_earnings': sum(log.earnings for log in logs),
        'today': timezone.now().date()
    }
    return render(request, 'steppia_app/work_tracker.html', context)

@login_required
def edit_work_log(request, pk):
    log = get_object_or_404(WorkLog, pk=pk, user=request.user)
    if request.method == 'POST':
        log.company_name = request.POST.get('company')
        log.date = request.POST.get('date')
        log.hours = float(request.POST.get('hours') or 0)
        log.earnings = int(request.POST.get('amount') or 0)
        log.save()
        return redirect('work_tracker')
    return render(request, 'steppia_app/edit_work_log.html', {'log': log})

@login_required
def delete_work_log(request, pk):
    get_object_or_404(WorkLog, pk=pk, user=request.user).delete()
    return redirect('work_tracker')

# --- 5. AI相談室（全50項目搭載版） ---
def ai_consult(request):
    ai_answer = ""
    user_q = ""
    
    FAQ_DATA = {
        "40代": "40代は人生経験が強みです。即戦力としての落ち着きをアピールしましょう。",
        "未経験": "「未経験」を「伸びしろ」と捉え、新しいことを吸収する意欲を伝えましょう。",
        # ... (中略)
        "未来": "一歩踏み出した今、あなたの未来はすでに変わり始めています。",
        "気分転換": "時には休むことも大切です。お気に入りの飲み物を飲んでリフレッシュしましょう。"
    }

    RANDOM_RESPONSES = [
        "その悩み、よくわかります。一歩ずつ進んでいきましょう！",
        "自己分析は冒険の地図作りです。焦らず丁寧に進めて大丈夫ですよ。",
        "あなたの強みは必ずあります。これまでの経験を信じてくださいね。",
        "今日は少し休んで、明日からまた新しい気持ちで挑戦しませんか？",
        "面接は『対話』です。素直なあなたでぶつかってみましょう！",
        "履歴書に書けることは、特別なことじゃなくていいんです。日常の頑張りを大切に。",
        "適性検査の結果は一つの指標に過ぎません。あまり落ち込まないでくださいね。",
        "今の努力は、必ず未来のあなたを助けてくれます。応援しています！",
        "不採用通知は『あなたを否定』したのではなく『縁がなかった』だけ。次に行きましょう！",
        "あなたのこれまでの歩みは、決して無駄ではありません。胸を張ってくださいね。",
        "焦りは禁物。深呼吸して、温かい飲み物でも飲みましょう。",
        "どんな小さな一歩でも、それは前進です。自分を褒めてあげてください。",
        "あなたのBEING（どうありたいか）を軸にすれば、道は必ず開けますよ。",
        "ステッピアの仲間もみんな頑張っています。一人じゃないですよ！",
    ]

    if request.method == 'POST':
        user_q = (request.POST.get('user_input') or request.POST.get('user_text', '')).strip()
        if user_q:
            template_match = AIConsultTemplate.objects.filter(question__icontains=user_q).first()
            if template_match:
                ai_answer = template_match.answer
            else:
                ai_answer = next((val for key, val in FAQ_DATA.items() if key in user_q), None)
                if not ai_answer:
                    ai_answer = random.choice(RANDOM_RESPONSES)

            AIConsultLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                user_question=user_q, 
                ai_response=ai_answer
            )
            
    return render(request, 'steppia_app/ai_consult.html', {'ai_answer': ai_answer, 'user_q': user_q})

# --- 6. マイページ ---
@login_required
def mypage(request):
    logs = AIConsultLog.objects.filter(user=request.user).order_by('-created_at')
    mypage_schedules = Schedule.objects.filter(user=request.user, detail__contains='コンサル予約').order_by('-date', '-time')
    user_applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    coupons = Coupon.objects.filter(user=request.user, is_used=False).order_by('-won_at')
    consultant_name = request.user.profile.assigned_consultant
    return render(request, 'steppia_app/mypage.html', {
        'logs': logs, 'mypage_schedules': mypage_schedules, 'applications': user_applications, 
        'coupons': coupons, 'consultant_name': consultant_name
    })

# --- 7. 進捗管理（冒険マップ） ---
@login_required
def progress(request):
    work_log_count = WorkLog.objects.filter(user=request.user).count()
    return render(request, 'steppia_app/progress.html', {
        'current_pos': work_log_count + 1,
        'has_applied': Application.objects.filter(user=request.user).exists(),
        'work_log_count': work_log_count
    })

# --- 8. ルーレット ---
@login_required
@never_cache
def roulette(request):
    member = request.user.profile
    return render(request, 'steppia_app/roulette.html', {'can_spin': member.can_spin_roulette()})

@login_required
@never_cache
def roulette_result(request, item):
    member = request.user.profile
    if not member.can_spin_roulette():
        return redirect('roulette')
    jst = pytz.timezone('Asia/Tokyo')
    member.last_roulette_date = timezone.now().astimezone(jst).date()
    member.save()
    is_win = any(k in item for k in ["賞", "面談", "券", "ギフト"])
    if is_win:
        Coupon.objects.create(user=request.user, prize_name=item)
    return render(request, 'steppia_app/roulette_result.html', {'item': item, 'is_win': is_win})

@login_required
def congrats(request):
    prize = request.GET.get('prize', 'ステキな景品')
    return render(request, 'steppia_app/congrats.html', {'prize': prize})

@login_required
def congrats_map(request):
    name = request.user.profile.first_name or request.user.username
    return render(request, 'steppia_app/congrats_map.html', {'user_name': name})

def roulette_lost(request):
    return render(request, 'steppia_app/roulette_lost.html')

# --- 9. 予約・スケジュール・設定 ---
def consult_top(request): return render(request, 'steppia_app/consult_top.html')
def consult_setting(request): return render(request, 'steppia_app/consult_setting.html')
def consult_reservation(request): return render(request, 'steppia_app/consult_reservation.html')

def consult_confirm(request):
    return render(request, 'steppia_app/consult_confirm.html', {
        'date': request.POST.get('date'), 'time': request.POST.get('time'), 'consultant': request.POST.get('consultant')
    })

@login_required
def consult_setting_done(request):
    if request.method == 'POST':
        consultant_name = request.POST.get('consultant')
        if consultant_name:
            member = request.user.profile
            member.assigned_consultant = consultant_name
            member.save()
            request.session['selected_consultant'] = consultant_name
    return render(request, 'steppia_app/consult_setting_done.html')

@login_required
def consult_reservation_done(request):
    if request.method == 'POST':
        Schedule.objects.create(
            user=request.user,
            date=request.POST.get('date'), 
            time=request.POST.get('time'), 
            detail=f"{request.POST.get('consultant')} コンサル予約"
        )
        coupon_id = request.POST.get('coupon_id')
        if coupon_id:
            Coupon.objects.filter(id=coupon_id, user=request.user).update(is_used=True)
    return render(request, 'steppia_app/consult_reservation_done.html')

@login_required
def schedule(request):
    if request.method == 'POST':
        Schedule.objects.create(user=request.user, date=request.POST.get('date'), time=request.POST.get('time'), detail=request.POST.get('detail'))
    schedules = Schedule.objects.filter(user=request.user).order_by('-date', '-time')
    return render(request, 'steppia_app/schedule.html', {'schedules': schedules})