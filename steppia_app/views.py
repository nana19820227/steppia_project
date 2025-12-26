from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum
import pytz

# すべてのモデルをインポート
from .models import Schedule, Member, Job, AIConsultTemplate, AIConsultLog, Applications, WorkLog, Coupon

# --- 1. 基本・メニュー ---
def top(request):
    """メインメニュー画面を表示する"""
    return render(request, 'steppia_app/top.html')

# --- 2. 会員登録 ---
def signup(request):
    """ステップ1: ログイン用のユーザーアカウント作成"""
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
    """ステップ2: 会員詳細情報の入力画面"""
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
    """会員登録完了：Memberを作成"""
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
    jobs = Job.objects.all()
    return render(request, 'steppia_app/job_list.html', {'jobs': jobs})

def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    return render(request, 'steppia_app/job_detail.html', {'job': job})

@login_required
def apply_to_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    Applications.objects.get_or_create(user=request.user, job=job)
    return redirect('apply_done')

def apply_done(request):
    consultant_name = request.session.get('selected_consultant', '担当コンサルタント')
    return render(request, 'steppia_app/apply_done.html', {'consultant_name': consultant_name})

# --- 4. お仕事ログ（累積判定＋修正・削除機能） ---
@login_required
def work_tracker(request):
    """1日の合計「4000円」または「2時間」超過判定"""
    show_warning = False
    if request.method == 'POST':
        date_str = request.POST.get('date')
        hours = request.POST.get('hours')
        amount = request.POST.get('amount')
        company = request.POST.get('company')
        if date_str and amount:
            WorkLog.objects.create(
                user=request.user,
                job=Job.objects.first(), 
                company_name=company if company else "（未入力）",
                date=date_str,
                hours=float(hours) if hours else 0,
                earnings=int(amount)
            )
            daily_stats = WorkLog.objects.filter(user=request.user, date=date_str).aggregate(
                total_pay=Sum('earnings'), total_hrs=Sum('hours')
            )
            total_pay = daily_stats['total_pay'] or 0
            total_hrs = daily_stats['total_hrs'] or 0
            if total_pay >= 4000 or total_hrs > 2:
                show_warning = True

    logs = WorkLog.objects.filter(user=request.user).order_by('-date')
    daily_summary = WorkLog.objects.filter(user=request.user).values('date').annotate(
        sum_pay=Sum('earnings'), sum_hrs=Sum('hours')
    )
    over_limit_dates = [
        item['date'] for item in daily_summary 
        if item['sum_pay'] >= 4000 or item['sum_hrs'] > 2
    ]
    for log in logs:
        log.is_over_limit = log.date in over_limit_dates
    
    context = {
        'logs': logs, 'show_warning': show_warning,
        'total_hours': sum(log.hours for log in logs) if logs else 0, 
        'total_earnings': sum(log.earnings for log in logs) if logs else 0,
        'limit_pay': 4000, 'limit_hrs': 2, 'today': timezone.now().date()
    }
    return render(request, 'steppia_app/work_tracker.html', context)

@login_required
def edit_work_log(request, pk):
    """ログの修正"""
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
    """ログの削除"""
    log = get_object_or_404(WorkLog, pk=pk, user=request.user)
    log.delete()
    return redirect('work_tracker')

# --- 5. AI相談室 ---
def ai_consult(request):
    ai_answer = ""
    user_q = ""
    FAQ_DATA = {
        "40代": "40代は人生経験が強みです。即戦力としての落ち着きをアピールしましょう。",
        "未経験": "「未経験」を「伸びしろ」と捉え、新しいことを吸収する意欲を伝えましょう。",
        "自信がない": "小さな成功体験を積み重ねることが大切です。まずは今日一歩踏み出した自分を褒めましょう。",
        "ブランク": "家事や育児で培った「段取り力」や「忍耐力」も立派なキャリアです。",
        "年齢制限": "法律で年齢制限は禁止されています。スキルと意欲があればチャンスは必ずあります。",
        "リスキリング": "デジタルスキルを身につけると事務職やIT職など選択肢が大きく広がります。まずは興味のある分野を探すことから始めましょう。",
        "Python": "初心者でも学びやすい言語です。自動化スキルは事務職でも重宝されます。",
        "Excel": "VLOOKUPやピボットテーブルができると、事務職の採用率がグッと上がります。",
        "AI": "AIを使いこなせる人材は今、非常に求められています。まずは触れてみることから！",
        "デザイン": "CanvaやPenpotなど、初心者向けのツールから始めると楽しく学べます。",
        "履歴書": "手書きよりパソコン作成が一般的です。清潔感のある写真を用意しましょう。",
        "職務経歴書": "「何をしてきたか」だけでなく「何ができるか」を具体的に書きましょう。",
        "自己PR": "自分の強みが会社にどう貢献できるか、具体例を交えて伝えましょう。",
        "志望動機": "「なぜこの会社なのか」を自分の言葉で語ることが内定への近道です。",
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
        "正社員": "安定を求めるなら正社員ですが、まずは派遣やパートからステップアップする道もあります。",
        "派遣": "短期間でスキルを身につけたい時や、色々な職場を経験したい時に有効です。",
        "パート": "時間の融通が利きやすいのが魅力。ブランク明けの復帰に最適です。",
        "失業保険": "ハローワークで手続きが必要です。受給しながらの再就職活動も可能です。",
        "社会保険": "106万円や130万円の壁を意識しつつ、保障の手厚い加入を目指すのも手です。",
        "有給休暇": "パートやアルバイトでも条件を満たせば取得できます。大切な権利です。",
        "最低賃金": "最低賃金は年々上がっています。自分の給料が基準を下回っていないか確認しましょう。",
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
        "気分転換": "時には休むことも大切です。お気に入りの飲み物を飲んだり、外の空気を吸ったりして、リフレッシュしましょう。"
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
                    if keyword in user_q: found_answer = answer; break
                ai_answer = found_answer if found_answer else "その悩み、一緒に考えましょう。担当コンサルタントに直接メッセージを送ってみてくださいね。"
            AIConsultLog.objects.create(user_question=user_q, ai_response=ai_answer)
    return render(request, 'steppia_app/ai_consult.html', {'ai_answer': ai_answer, 'user_q': user_q})

def ai_history(request): return redirect('mypage')

# --- 6. マイページ ---
@login_required
def mypage(request):
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
    work_log_count = WorkLog.objects.filter(user=request.user).count()
    current_pos = work_log_count + 1
    status = {
        'is_signed_up': Member.objects.filter(user=request.user).exists(),
        'has_applied': Applications.objects.filter(user=request.user).exists(),
        'work_log_count': work_log_count,
    }
    return render(request, 'steppia_app/progress.html', {
        'status': status, 'current_pos': current_pos, 'work_log_count': work_log_count
    })

# --- 8. コンサル予約・ルーレット ---
def consult_top(request): return render(request, 'steppia_app/consult_top.html')
def consult_setting(request):
    if request.method == 'POST':
        request.session['selected_consultant'] = request.POST.get('consultant_name')
        return redirect('consult_setting_done')
    return render(request, 'steppia_app/consult_setting.html')

def consult_reservation(request): return render(request, 'steppia_app/consult_reservation.html')

def consult_confirm(request):
    return render(request, 'steppia_app/consult_confirm.html', {
        'date': request.POST.get('date'), 'time': request.POST.get('time'), 'consultant': request.POST.get('consultant')
    })

def consult_setting_done(request): return render(request, 'steppia_app/consult_setting_done.html')

def consult_reservation_done(request):
    if request.method == 'POST':
        Schedule.objects.create(date=request.POST.get('date'), time=request.POST.get('time'), detail=f"{request.POST.get('consultant')} コンサル予約")
        coupon_id = request.POST.get('coupon_id')
        if coupon_id:
            coupon = Coupon.objects.filter(id=coupon_id, user=request.user).first()
            if coupon: coupon.is_used = True; coupon.save()
    return render(request, 'steppia_app/consult_reservation_done.html')

def schedule(request):
    if request.method == 'POST': Schedule.objects.create(date=request.POST.get('date'), time=request.POST.get('time'), detail=request.POST.get('detail'))
    return render(request, 'steppia_app/schedule.html', {'schedules': Schedule.objects.all().order_by('-date', '-time')})

@login_required
def roulette(request):
    jst = pytz.timezone('Asia/Tokyo'); now_jst = timezone.now().astimezone(jst)
    member = Member.objects.filter(user=request.user).first()
    # 1日1回判定
    can_spin = not (member and member.last_roulette_date == now_jst.date())
    return render(request, 'steppia_app/roulette.html', {'can_spin': can_spin})

@login_required
def roulette_result(request, item):
    """🆕 ルーレット結果画面（1日1回制限を厳格化）"""
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = timezone.now().astimezone(jst)
    member = Member.objects.filter(user=request.user).first()

    # すでに今日回していたら、ルーレットTOPへ戻す（不正防止）
    if member and member.last_roulette_date == now_jst.date():
        return redirect('roulette')

    # 回した日付を保存
    if member:
        member.last_roulette_date = now_jst.date()
        member.save()

    # クーポン発行
    is_win = "賞" in item or "面談" in item
    if is_win:
        Coupon.objects.get_or_create(
            user=request.user, 
            prize_name=item, 
            is_used=False,
            won_at=now_jst.date()
        )
    return render(request, 'steppia_app/roulette_result.html', {'item': item, 'is_win': is_win})

@login_required
def congrats(request): return render(request, 'steppia_app/congrats.html', {'prize': request.GET.get('prize', '豪華賞品')})

def roulette_lost(request): return render(request, 'steppia_app/roulette_lost.html')

@login_required
def congrats_map(request):
    """ゴール時のお祝い画面にお名前を表示"""
    member = Member.objects.filter(user=request.user).first()
    user_name = member.first_name if member else request.user.username
    return render(request, 'steppia_app/congrats_map.html', {'user_name': user_name})