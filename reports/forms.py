from django import forms
from django.contrib.auth.models import User
from .models import DailyReport
from .models import ReportTemplate

# 一覧/作成で使う（日報）
class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        exclude = ["report_date", "user"]


# 新規登録で使う
class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("password_confirm")
        if password != confirm:
            raise forms.ValidationError("パスワードが一致しません")
        return cleaned_data

#テンプレート
class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ["template1", "is_formal", "is_casual"]
        widgets = {
            "template1": forms.Textarea(attrs={"class": "template-textarea", "rows": 12}),
        }