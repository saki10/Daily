import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DailyReport, ReportTemplate
from django.contrib.auth.forms import AuthenticationForm
from .models import DailyReport
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm
from django.contrib.auth.forms import PasswordChangeForm

User = get_user_model()

# ==============================
# パスワード変更画面用
# ==============================

PASSWORD_RULE_MESSAGE = "英語と数字を含む8文字以上にしましょう"
PASSWORD_MISMATCH_MESSAGE = "パスワードと確認用パスワードが一致しません"


def validate_password_rule(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="現在のパスワード",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "現在のパスワードを入力してください",
            }
        ),
        error_messages={
            "required": "現在のパスワードを入力してください",
        },
    )

    new_password1 = forms.CharField(
        label="新しいパスワード",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "新しいパスワードを入力してください",
            }
        ),
        error_messages={
            "required": "パスワードを入力してください",
        },
    )

    new_password2 = forms.CharField(
        label="新しいパスワード（確認用）",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "確認用パスワードを入力してください",
            }
        ),
        error_messages={
            "required": "確認用パスワードを入力してください",
        },
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")

        if password and not validate_password_rule(password):
            raise forms.ValidationError(PASSWORD_RULE_MESSAGE)

        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", PASSWORD_MISMATCH_MESSAGE)

        return cleaned_data
# ==============================
# 新規登録画面用
# ==============================

SIGNUP_PASSWORD_RULE_MESSAGE = "8文字以上で英大文字・英小文字を含めて入力してください"


def validate_signup_password_rule(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    return True


class SignUpForm(forms.ModelForm):
    username = forms.CharField(
        label="名前",
        required=True,
        error_messages={
            "required": "名前を入力してください",
        },
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "名前を入力してください",
            }
        ),
    )

    email = forms.EmailField(
        label="メールアドレス",
        required=True,
        error_messages={
            "required": "メールアドレスを入力してください",
            "invalid": "メールアドレス形式で入力してください",
        },
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "メールアドレスを入力してください",
            }
        ),
    )

    password1 = forms.CharField(
        label="パスワード",
        required=True,
        error_messages={
            "required": "パスワードを入力してください",
        },
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "パスワードを入力してください",
            }
        ),
    )

    password2 = forms.CharField(
        label="確認用パスワード",
        required=True,
        error_messages={
            "required": "確認用パスワードを入力してください",
        },
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "確認用パスワードを再入力してください",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")

        return email

    def clean_password1(self):
        password = self.cleaned_data.get("password1")

        if password and not validate_signup_password_rule(password):
            raise forms.ValidationError(SIGNUP_PASSWORD_RULE_MESSAGE)

        return password

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error(
                "password2",
                "パスワードと確認用パスワードが一致しません"
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user
class EmailChangeForm(forms.ModelForm):
    email = forms.EmailField(
        label="メールアドレス",
        error_messages={
            "required": "メールアドレスを入力してください",
            "invalid": "メールアドレス形式で入力してください",
        },
    )
#メールアドレス変更制約
    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")

        return email

#名前変更フォーム制約
class UsernameChangeForm(forms.ModelForm):
    username = forms.CharField(
        label="名前",
        error_messages={
            "required": "名前を入力してください",
        },
    )

#パスワード変更フォーム制約
class CustomPasswordResetForm(PasswordResetForm):
    new_password1 = forms.CharField(
        label="新しいパスワード",
        widget=forms.PasswordInput,
        error_messages={
            "required": "パスワードを入力してください",
        },
    )

    new_password2 = forms.CharField(
        label="新しいパスワード（確認用）",
        widget=forms.PasswordInput,
        error_messages={
            "required": "確認用パスワードを入力してください",
        },
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")

        if password and not validate_password_rule(password):
            raise forms.ValidationError(PASSWORD_RULE_MESSAGE)

        return password

    def clean(self):
        cleaned_data = self.cleaned_data
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", PASSWORD_MISMATCH_MESSAGE)

        return cleaned_data
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
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "登録済みのメールアドレスを入力",
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        UserModel = get_user_model()

        if not UserModel.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "このメールアドレスは登録されていません。新規登録をおこなってください。"
            )

        return email

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
            
#未登録メールの場合にエラー表示したい場合
User = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "このメールアドレスは登録されていません。新規登録をおこなってください。"
            )

        return email

