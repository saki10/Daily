from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

class DailyReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # ⭐ カレンダー連携
    report_date = models.DateField(default=timezone.localdate) 

    today_work = models.TextField("今日やったこと", blank=True)
    reflection = models.TextField("振り返り", blank=True)
    tomorrow_plan = models.TextField("明日の予定", blank=True)
    note = models.TextField("備考", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "report_date")
        ordering = ["-report_date"]

    def __str__(self):
        return f"{self.user} - {self.report_date}"
    

    #AI連携設定
class UserIntegration(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    slack_enabled = models.BooleanField(default=False)
    teams_enabled = models.BooleanField(default=False)
    gmail_enabled = models.BooleanField(default=False)

    # ✅ 追加：Webhook URL（ユーザーごと）
    slack_webhook_url = models.URLField(blank=True, default="")
    teams_webhook_url = models.URLField(blank=True, null=True)
    def __str__(self):
        return self.user.username   


    #テンプレート
class ReportTemplate(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    template1 = models.TextField(blank=True, default="")
    is_formal = models.BooleanField(default=False)
    is_casual = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} のテンプレート"