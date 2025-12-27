from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
from django.views.decorators.cache import never_cache
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
        "自信がない": "小さな成功体験を積み重ねることが大切です。まずは今日一歩踏み出した自分を褒めましょう。",
        "ブランク": "家事や育児で培った「段取り力」や「忍耐力」も立派なキャリアです。",
        "年齢制限": "法律で年齢制限は禁止されています。スキルと意欲があればチャンスは必ずあります。",
        "リスキリング": "デジタルスキルを身につけると事務職やIT職など選択肢が大きく広がります。",
        "Python": "初心者でも学びやすい言語です。自動化スキルは事務職でも重宝されます。",
        "Excel": "VLOOKUPやピボットテーブルができると、採用率がグッと上がります。",
        "AI": "AIを使いこなせる人材は今、非常に求められています。まずは触れてみることから！",
        "デザイン": "CanvaやPenpotなど、初心者向けのツールから始めると楽しく学べます。",
        "履歴書": "手書きよりパソコン作成が一般的です。清潔感のある写真を用意しましょう。",
        "職務経歴書": "「何をしてきたか」だけでなく「何ができるか」を具体的に書きましょう。",
        "自己PR": "自分の強みが会社にどう貢献できるか、具体例を交えて伝えましょう。",
        "志望動機": "「なぜこの会社なのか」を自分の言葉で語ることが内定への道です。",
        "面接": "面接は対話です。笑顔と元気な挨拶があれば、第一印象はバッチリです。",
        "オンライン面接": "背景や照明に気をつけ、カメラを見て話すと意欲が伝わります。",
        "逆質問": "「入社までに準備しておくことは？」など、前向きな質問を用意しましょう。",
        "シングルマザー": "理解のある企業は増えています。自治体の助成金なども活用しましょう。",
        "両立": "最初から100%を目指さず、周りの協力や便利なサービスを頼るのも戦略です。",
        "時短勤務": "ライフスタイルに合わせた働き方を相談できる企業を一緒に探しましょう。",
        "在宅ワーク": "通勤がない分、家庭の時間が持てます。ITスキルがあると採用されやすいです。",
        "副業": "まずは月1〜3万円を目指して、得意なことから始めてみるのがおすすめです。",
        "ワークライフバランス": "仕事も家庭も大切にするために、優先順位を決めておきましょう。",
        "給料": "相場を知ることは大切です。スキルを上げて昇給を目指す道もあります。",
        "福利厚生": "育休や介護休暇の取得実績があるかチェックしておくと安心です。",
        "正社員": "安定を求めるなら正社員ですが、まずは派遣やパートから進む道もあります。",
        "派遣": "短期間でスキルを身につけたい時や、色々な職場を経験したい時に有効です。",
        "パート": "時間の融通が利きやすいのが魅力。ブランク明けの復帰に最適です。",
        "失業保険": "ハローワークで手続きが必要です。受給しながらの活動も可能です。",
        "社会保険": "106万円や130万円の壁を意識しつつ、保障の手厚い加入を目指すのも手です。",
        "有給休暇": "パートやアルバイトでも条件を満たせば取得できます。大切な権利です。",
        "最低賃金": "最低賃金は年々上がっています。基準を下回っていないか確認しましょう。",
        "資格": "実務に直結する資格から取るのが効率的です。コンサルタントに相談してください。",
        "マネジメント": "後輩の指導経験などもマネジメント経験として評価されます。",
        "転職回数": "多いことを気にするより、その経験をどう活かすかを前向きに伝えましょう。",
        "キャリアチェンジ": "今のスキルをベースに、隣接する職種へスライドするのがスムーズです。",
        "緊張": "「緊張するのは頑張りたい証拠」と受け入れて、深呼吸をしましょう。",
        "不採用": "あなたの価値を否定されたわけではありません。縁がなかっただけと切り替えましょう。",
        "焦り": "周りと比べず、自分のペースで進むことが一番の近道です。",
        "人間関係": "新しい職場では「聞き上手」から始めると、馴染みやすくなります。",
        "コンサルタント": "迷ったらすぐに相談してください。私たちはあなたの味方です。",
        "冒険マップ": "ログをつけると進みます。毎日の積み重ねがゴールへの道です。",
        "ルーレット": "毎日の楽しみとして活用してください。お得なクーポンも当たります。",
        "お仕事ログ": "日々の頑張りを記録しましょう。自分の成長が目に見えてわかります。",
        "求人": "Steppiaには未経験や40代歓迎の求人を厳選して掲載しています。",
        "ログ": "記録をつける習慣が、あなたの「継続力」の証明になります。",
        "マップ": "STEP 30を目指して進みましょう。ゴールには素敵な演出が待っています！",
        "相談": "どんな小さなことでもOK。AI相談室やコンサルタントを頼ってください。",
        "未来": "一歩踏み出した今、あなたの未来はすでに変わり始めています。",
        "気分転換": "時には休むことも大切です。お気に入りの飲み物を飲んでリフレッシュしましょう。"
    }
    if request.method == 'POST':
        user_q = (request.POST.get('user_input') or request.POST.get('user_text', '')).strip()
        if user_q:
            template_match = AIConsultTemplate.objects.filter(question__icontains=user_q).first()
            if template_match:
                ai_answer = template_match.answer
            else:
                ai_answer = next((val for key, val in FAQ_DATA.items() if key in user_q), "その悩み、一緒に考えましょう。担当コンサルタントに相談してくださいね。")
            AIConsultLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                user_question=user_q, 
                ai_response=ai_answer
            )
    return render(request, 'steppia_app/ai_consult.html', {'ai_answer': ai_answer, 'user_q': user_q})

@login_required
def ai_history(request):
    return redirect('mypage')

# --- 6. マイページ ---
@login_required
def mypage(request):
    """ユーザー情報統合表示（担当コンサルタント名を取得）"""
    logs = AIConsultLog.objects.filter(user=request.user).order_by('-created_at')
    mypage_schedules = Schedule.objects.filter(user=request.user, detail__contains='コンサル予約').order_by('-date', '-time')
    user_applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    coupons = Coupon.objects.filter(user=request.user, is_used=False).order_by('-won_at')
    
    # 🆕 データベース（Member）から担当者名を取得
    consultant_name = request.user.profile.assigned_consultant
    
    return render(request, 'steppia_app/mypage.html', {
        'logs': logs, 
        'mypage_schedules': mypage_schedules, 
        'applications': user_applications, 
        'coupons': coupons,
        'consultant_name': consultant_name # 🆕 HTMLへ渡す
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
    """🆕 担当コンサルタントをデータベースに保存する"""
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