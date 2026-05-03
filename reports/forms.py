from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DailyReport, ReportTemplate
from django.contrib.auth.forms import AuthenticationForm
from .models import DailyReport
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordResetForm


# 一覧/作成で使う（日報）
class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        exclude = ["report_date", "user"]


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "メールアドレスを入力",
                "autocomplete": "email",
            }
        ),
    )

    password = forms.CharField(
        label="パスワード",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "パスワードを入力",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": "メールアドレスまたはパスワードが正しくありません。",
        "inactive": "このアカウントは無効です。",
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            UserModel = get_user_model()
            users = UserModel.objects.filter(email__iexact=email)

            self.user_cache = None

            for user in users:
                authenticated_user = authenticate(
                    self.request,
                    username=user.get_username(),
                    password=password,
                )

                if authenticated_user is not None:
                    self.user_cache = authenticated_user
                    break

            if self.user_cache is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
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
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "メールアドレスを入力",
            }
        ),
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

        self.fields["username"].widget.attrs.update({
            "class": "form-input",
            "placeholder": "ユーザー名を入力",
        })

        self.fields["password1"].widget.attrs.update({
            "class": "form-input",
            "placeholder": "英数字を含む8文字以上で入力",
        })

        self.fields["password2"].widget.attrs.update({
            "class": "form-input",
            "placeholder": "再度パスワードを入力",
        })
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email:
            email = email.strip().lower()

            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError(
                    "このメールアドレスはすでに登録されています。"
                )

        return email
# パスワード再設定で使う
class CustomPasswordResetForm(PasswordResetForm):
    """
    同じメールアドレスのユーザーが複数存在する場合でも、
    最初の1アカウントにだけパスワード再設定メールを送信する。
    """

    def get_users(self, email):
        UserModel = get_user_model()

        users = (
            UserModel._default_manager
            .filter(email__iexact=email, is_active=True)
            .order_by("date_joined", "id")
        )

        for user in users:
            if user.has_usable_password():
                yield user
                return