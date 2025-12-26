from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# 1. 会員情報（ユーザープロフィール）
class Member(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, 
        verbose_name="ユーザー", related_name="profile", 
        null=True, blank=True
    )
    last_name = models.CharField('姓', max_length=100)
    first_name = models.CharField('名', max_length=100)
    last_name_kana = models.CharField('せい', max_length=100)
    first_name_kana = models.CharField('めい', max_length=100)
    address = models.CharField('住所', max_length=255, blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    email = models.EmailField('メールアドレス', unique=True)
    daily_wage = models.IntegerField('賃金日額', default=0)
    
    # ルーレットリセット用（日付で管理）
    last_roulette_date = models.DateField('最後にルーレットを回した日', null=True, blank=True)

    class Meta:
        verbose_name = "会員情報"
        verbose_name_plural = "会員情報"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def can_spin_roulette(self):
        """
        今日ルーレットを回せるか判定する（日本時間基準）
        """
        if not self.last_roulette_date:
            return True
        
        # 🆕 修正ポイント: localdate() を使うことで settings.py の Asia/Tokyo を基準にします
        # これにより、日本の深夜0時を過ぎた瞬間に日付が切り替わります。
        today = timezone.localdate()
        
        # 保存されている日付が「今日」より前であれば回せる
        return self.last_roulette_date < today

# 2. 求人情報
class Job(models.Model):
    title = models.CharField('仕事のタイトル', max_length=100)
    company = models.CharField('会社名', max_length=100)
    location = models.CharField('勤務地', max_length=100)
    salary = models.CharField('給与', max_length=100)
    description = models.TextField('仕事の内容')

    class Meta:
        verbose_name = "求人情報"
        verbose_name_plural = "求人情報"

    def __str__(self):
        return self.title

# 3. 応募履歴・進捗管理
class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー", related_name="applications")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, verbose_name="応募先企業")
    applied_at = models.DateTimeField('応募日時', auto_now_add=True)
    current_step = models.IntegerField('現在のステップ', default=1)
    status = models.CharField('選考ステータス', max_length=50, default='連絡待ち')

    class Meta:
        verbose_name = "応募履歴・進捗"
        verbose_name_plural = "応募履歴・進捗"
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user.username} - {self.job.company} (Step: {self.current_step})"

# 4. スケジュール
class Schedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー", null=True, blank=True)
    date = models.DateField('日付')
    time = models.TimeField('時間')
    detail = models.CharField('内容', max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "スケジュール"
        verbose_name_plural = "スケジュール"

    def __str__(self):
        return f"{self.date} {self.time} - {self.detail}"

# 5. AI相談
class AIConsultTemplate(models.Model):
    question = models.CharField('よくある質問', max_length=200)
    answer = models.TextField('回答内容')

    class Meta:
        verbose_name = "AI相談テンプレート"
        verbose_name_plural = "AI相談テンプレート"

    def __str__(self):
        return self.question

class AIConsultLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー", null=True, blank=True)
    user_question = models.TextField('相談内容')
    ai_response = models.TextField('AIの回答')
    created_at = models.DateTimeField('相談日時', auto_now_add=True)

    class Meta:
        verbose_name = "AI相談ログ"
        verbose_name_plural = "AI相談ログ"

    def __str__(self):
        return f"{self.created_at.strftime('%Y/%m/%d %H:%M')}の相談"

# 6. お仕事ログ
class WorkLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, verbose_name="求人", null=True, blank=True)
    company_name = models.CharField('会社名', max_length=255, blank=True, null=True)
    date = models.DateField('就労日')
    hours = models.FloatField('就労時間')
    earnings = models.IntegerField('総支給額')

    class Meta:
        verbose_name = "お仕事ログ"
        verbose_name_plural = "お仕事ログ"

    def __str__(self):
        company = self.company_name if self.company_name else "不明"
        return f"{self.date} - {company}"

# 7. クーポン（景品）
class Coupon(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="ユーザー")
    prize_name = models.CharField('景品名', max_length=100)
    won_at = models.DateTimeField('獲得日時', auto_now_add=True)
    is_used = models.BooleanField('使用済み', default=False)

    class Meta:
        verbose_name = "獲得クーポン"
        verbose_name_plural = "獲得クーポン"

    def __str__(self):
        return f"{self.user.username} - {self.prize_name}"

# --- シグナル設定 ---
@receiver(post_save, sender=User)
def create_user_member(sender, instance, created, **kwargs):
    if created:
        Member.objects.create(user=instance, email=instance.email)

@receiver(post_save, sender=User)
def save_user_member(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()