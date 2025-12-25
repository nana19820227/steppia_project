from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
import pytz

# すべてのモデルをインポート
from .models import Schedule, Member, Job, AIConsultTemplate, AIConsultLog, Applications, WorkLog, Coupon

# --- 1. 基本・メニュー ---
def top(request):
    """メインメニュー画面を表示する"""
    return render(request, 'steppia_app/top.html')

# --- 2. 会員登録 ---
def signup(request):
    """会員登録入力画面"""
    return render(request, 'steppia_app/signup.html')

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

def signup_done(request):
    """会員登録完了：新しいMemberを作成しログインユーザーと紐付け"""
    if request.method == 'POST':
        Member.objects.create(
            # ログインしているユーザーを会員情報に紐付ける
            user=request.user if request.user.is_authenticated else None,
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

    # 現在のログインユーザーに紐づく会員情報を取得
    member = Member.objects.filter(user=request.user).first()
    daily_wage = member.daily_wage if member else 0
    limit_80 = int(daily_wage * 0.8)
    logs = WorkLog.objects.filter(user=request.user).order_by('-date')
    
    for log in logs:
        # 賃金日額の80%を超えているか判定
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
    
    FAQ_DATA = {
        "40代": "40代は経験の宝庫です。スキルだけでなく、これまでの柔軟な対応力をアピールしましょう。",
        "未経験": "異業種でも、共通する「調整力や管理能力（ポータブルスキル）」を言語化するのが鍵です。",
        "ブランク": "ブランク期間に得た生活の知恵や、学び直しの意欲を前向きに伝えましょう。",
        "強み": "当たり前にこなしてきたことの中に強みがあります。まずは「得意なことリスト」を作りましょう。",
        "自信": "完璧を目指さず、まずは「今の自分にできること」を棚卸しすることから始めましょう。",
        "再就職": "復職支援サービスや、主婦歓迎の求人サイトも活用して、スモールステップで始めましょう。",
        "適職": "価値観（何を大切にしたいか）を軸に考えると、納得感のある選択ができますよ。",
        "キャリアチェンジ": "40代は後半戦のスタートです。新しい挑戦に遅すぎることはありません。",
        "市場価値": "実務経験に加え、人間関係の構築能力などの「ソフトスキル」が非常に重宝されます。",
        "やりたいこと": "「やりたくないこと」を消去法で選ぶのも、立派なキャリア戦略の一つです。",
        "履歴書": "丁寧に書くのはもちろん、写真は清潔感を重視し、明るい表情のものを選びましょう。",
        "職務経歴書": "直近の経験や応募先に役立つ実績を重点的に。枚数は2枚程度にまとめましょう。",
        "志望動機": "「なぜその会社か」と「自分が入社してどう貢献できるか」をセットで伝えましょう。",
        "PR": "具体的な数字やエピソードを交えると、あなたの活躍する姿がイメージされやすくなります。",
        "資格": "資格がなくても、長年の実務経験や周囲との協調性は強力な武器になります。",
        "転職回数": "回数の多さは「適応能力の高さ」としてポジティブに言い換えましょう。",
        "写真": "証明写真機よりも、フォトスタジオで撮影すると第一印象がぐっと良くなります。",
        "PCスキル": "基本的なOffice操作ができるなら、具体的な作業内容を明記してアピールしましょう。",
        "自己分析": "これまでの人生の「喜怒哀楽」を振り返ると、自分の本当の価値観が見えてきます。",
        "面接": "面接では、結論から先に話す「PREP法」を意識すると好印象ですよ。",
        "服装": "清潔感のあるジャケットスタイルが安心です。迷ったら少しフォーマル寄りにしましょう。",
        "オンライン面接": "背景を整理し、カメラを直視して話すと、相手に熱意が伝わりやすくなります。",
        "逆質問": "「御社で活躍している方の共通点は？」など、意欲が伝わる質問を用意しましょう。",
        "緊張": "深呼吸を忘れずに。面接官も「あなたと一緒に働けるか」を知りたいだけです。",
        "退職理由": "不満ではなく「新しい環境で〇〇に挑戦したい」という前向きな言葉に変えましょう。",
        "年収交渉": "自分の実績を根拠に希望額を伝えましょう。相談のタイミングも重要です。",
        "自己紹介": "1分程度で、経歴と応募への意気込みを簡潔にまとめて話せるようにしましょう。",
        "長所": "仕事にどう活かせるかをセットで。短所は改善への努力を添えて話しましょう。",
        "選考状況": "隠す必要はありません。「第一志望ですが、並行して進めています」と誠実に。",
        "介護": "両立支援制度がある会社も増えています。最初から無理のない働き方を相談しましょう。",
        "子育て": "お子さんの成長に合わせた、柔軟な働き方の「短時間正社員」なども検討しましょう。",
        "残業": "業務効率を上げ、時間内で成果を出す姿勢を具体的にアピールしましょう。",
        "リモート": "在宅ワーク可能な求人も増えています。ITツールへの抵抗感をなくしておくと有利です。",
        "体力": "立ち仕事かデスクワークかなど、自分の体調に合った環境を優先して選びましょう。",
        "バランス": "自分が仕事以外に「絶対に譲れない時間」は何かを明確にしましょう。",
        "正社員": "パートからの登用制度があるか、これまでの実績をどう評価されるか確認しましょう。",
        "派遣": "ライフスタイルに合わせて期間を決めて働ける、派遣という選択肢も有効です。",
        "副業": "複数の収入源を持つことで、精神的な安定とスキルアップに繋がります。",
        "時短": "勤務時間が短い分、密度濃く働くという決意を伝えて交渉しましょう。",
        "年下": "年下の面接官や上司に対しても、謙虚さとプロ意識を持って対等に接しましょう。",
        "馴染めるか": "最初は聞き役に徹し、職場のルールや空気を理解することから始めましょう。",
        "マネジメント": "リーダー経験がなくても、後輩の育成経験などは立派な管理能力です。",
        "パワハラ": "口コミサイトや面接時の社員の雰囲気で、社風を事前に確認しましょう。",
        "平均年収": "40代女性の平均を参考にしつつ、自分のスキルに見合った額を把握しましょう。",
        "最終面接": "経営層が見るのは「覚悟」です。その会社で長く働きたい熱意を伝えましょう。",
        "内定辞退": "辞退する場合は、感謝を込めて早めに誠実な連絡を入れましょう。",
        "試用期間": "周囲と積極的にコミュニケーションを取り、業務の流れをいち早く掴みましょう。",
        "健康": "セルフケアを大切に。長く元気に働けることが、会社への貢献にも繋がります。",
        "人間関係": "適度な距離感と挨拶を大切に。円滑な関係は仕事の効率も上げます。",
        "やりがい": "仕事を通じて誰を笑顔にしたいか、自分なりの目的を持つと楽しくなります。",
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
                if found_answer:
                    ai_answer = found_answer
                else:
                    ai_answer = "その件については、より詳細な状況を把握する必要があるため、担当コンサルタントに直接ご相談してみてくださいね。"

            AIConsultLog.objects.create(user_question=user_q, ai_response=ai_answer)

    return render(request, 'steppia_app/ai_consult.html', {'ai_answer': ai_answer, 'user_q': user_q})

def ai_history(request):
    """履歴表示用にマイページへリダイレクト"""
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
    """マップの各ステップの達成状況を判定"""
    is_signed_up = Member.objects.filter(user=request.user).exists()
    has_logs = AIConsultLog.objects.exists()
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
    for i in range(1, 31):
        if status.get(f'step{i}'): current_pos = i
    return render(request, 'steppia_app/progress.html', {'status': status, 'current_pos': current_pos})

# --- 8. コンサル予約・スケジュール ---
def consult_top(request): 
    return render(request, 'steppia_app/consult_top.html')

def consult_setting(request):
    """担当コンサルタントの選択"""
    if request.method == 'POST':
        request.session['selected_consultant'] = request.POST.get('consultant_name')
        return redirect('consult_setting_done')
    return render(request, 'steppia_app/consult_setting.html')

def consult_reservation(request): 
    return render(request, 'steppia_app/consult_reservation.html')

def consult_confirm(request):
    """予約内容の確認"""
    return render(request, 'steppia_app/consult_confirm.html', {
        'date': request.POST.get('date'), 
        'time': request.POST.get('time'), 
        'consultant': request.POST.get('consultant')
    })

def consult_setting_done(request): 
    return render(request, 'steppia_app/consult_setting_done.html')

def consult_reservation_done(request):
    """予約の保存とクーポンの使用処理"""
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
    """一般的なスケジュール管理"""
    if request.method == 'POST':
        Schedule.objects.create(
            date=request.POST.get('date'), 
            time=request.POST.get('time'), 
            detail=request.POST.get('detail')
        )
    return render(request, 'steppia_app/schedule.html', {'schedules': Schedule.objects.all().order_by('-date', '-time')})

# --- 9. 🎁 ルーレット関連（1日1回日本時間制限版） ---
@login_required
def roulette(request):
    """1日1回制限の判定を行いルーレット画面を表示"""
    # 日本時間（JST）の取得
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = timezone.now().astimezone(jst)
    today_jst = now_jst.date()

    # 会員情報を取得
    member = Member.objects.filter(user=request.user).first()
    
    # 今日すでに回したか判定
    can_spin = True
    if member and member.last_roulette_date == today_jst:
        can_spin = False
    
    return render(request, 'steppia_app/roulette.html', {'can_spin': can_spin})

@login_required
def roulette_result(request, item):
    """ルーレット結果の保存と実行日の更新"""
    # 日本時間で今日の日付を取得
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = timezone.now().astimezone(jst)
    today_jst = now_jst.date()

    # 最後に回した日を更新
    member = Member.objects.filter(user=request.user).first()
    if member:
        member.last_roulette_date = today_jst
        member.save()

    # 当選品が「賞」または「面談」を含む場合にクーポンを発行
    is_win = "賞" in item or "面談" in item
    if is_win:
        Coupon.objects.get_or_create(user=request.user, prize_name=item, is_used=False)
    
    context = {'item': item, 'is_win': is_win}
    return render(request, 'steppia_app/roulette_result.html', context)

@login_required
def congrats(request):
    """当選おめでとう画面"""
    prize = request.GET.get('prize', '豪華賞品')
    return render(request, 'steppia_app/congrats.html', {'prize': prize})

def roulette_lost(request):
    """残念画面"""
    return render(request, 'steppia_app/roulette_lost.html')

# --- 10. 🌸 冒険マップお祝い関連 ---
@login_required
def congrats_map(request):
    """全ステップ達成のお祝い画面"""
    return render(request, 'steppia_app/congrats_map.html')