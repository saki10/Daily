from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DailyReport, ReportTemplate


# 一覧/作成で使う（日報）
class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        exclude = ["report_date", "user"]


# テンプレート
class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ["template1", "is_formal", "is_casual"]
        widgets = {
            "template1": forms.Textarea(attrs={"class": "template-textarea", "rows": 12}),
        }


# 新規登録で使う
class SignupForm(UserCreationForm):
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"class": "form-input"})
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {
            "username": "ユーザー名",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].label = "ユーザー名"
        self.fields["password1"].label = "パスワード"
        self.fields["password2"].label = "パスワード確認"

        self.fields["username"].widget.attrs.update({"class": "form-input"})
        self.fields["password1"].widget.attrs.update({"class": "form-input"})
        self.fields["password2"].widget.attrs.update({"class": "form-input"})