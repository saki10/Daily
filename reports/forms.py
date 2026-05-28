import re

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    UserCreationForm,
)

from .models import DailyReport, ReportTemplate


User = get_user_model()


# ==============================
# パスワード共通ルール
# ==============================

PASSWORD_RULE_MESSAGE = "英語と数字を含む8文字以上にしましょう"
PASSWORD_MISMATCH_MESSAGE = "パスワードと確認用パスワードが一致しません"
NEW_PASSWORD_MISMATCH_MESSAGE = "新しいパスワードと確認用パスワードが一致しません"


def validate_password_rule(password):
    """
    パスワード規定：
    ・8文字以上
    ・英字を含む
    ・数字を含む
    """
    if not password:
        return False

    has_letter = re.search(r"[A-Za-z]", password)
    has_number = re.search(r"\d", password)

    return len(password) >= 8 and has_letter and has_number


def add_error_once(form, field_name, message):
    """
    同じエラーメッセージが重複表示されないように追加する。
    """
    existing_errors = []

    if getattr(form, "_errors", None) is not None and field_name in form._errors:
        existing_errors = [str(error) for error in form._errors[field_name]]

    if message not in existing_errors:
        form.add_error(field_name, message)


# ==============================
# パスワード変更画面用
# ==============================

class CustomPasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label="現在のパスワード",
        error_messages={
            "required": "現在のパスワードを入力してください",
        },
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "現在のパスワードを入力してください",
            }
        ),
    )

    new_password1 = forms.CharField(
        label="新しいパスワード",
        error_messages={
            "required": "新しいパスワードを入力してください",
        },
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "新しいパスワードを入力してください",
            }
        ),
    )

    new_password2 = forms.CharField(
        label="新しいパスワード（確認）",
        error_messages={
            "required": "確認用パスワードを入力してください",
        },
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "確認用パスワードを入力してください",
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")

        if old_password and not self.user.check_password(old_password):
            raise forms.ValidationError("現在のパスワードが正しくありません。")

        return old_password

    def clean(self):
        cleaned_data = super().clean()

        new_password1 = self.data.get(self.add_prefix("new_password1"), "")
        new_password2 = self.data.get(self.add_prefix("new_password2"), "")

        if new_password1 and not validate_password_rule(new_password1):
            self.add_error(
                "new_password1",
                PASSWORD_RULE_MESSAGE
            )

        if new_password1 and new_password2 and new_password1 != new_password2:
            self.add_error(
                "new_password2",
                NEW_PASSWORD_MISMATCH_MESSAGE
            )

        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)

        if commit:
            self.user.save()

        return self.user
# ==============================
# 新規登録画面用
# ==============================

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

        if email:
            email = email.strip().lower()

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = self.data.get(self.add_prefix("password1"), "")
        password2 = self.data.get(self.add_prefix("password2"), "")

        if password1 and not validate_password_rule(password1):
            add_error_once(
                self,
                "password1",
                PASSWORD_RULE_MESSAGE,
            )

        if password1 and password2 and password1 != password2:
            add_error_once(
                self,
                "password2",
                PASSWORD_MISMATCH_MESSAGE,
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.username = self.cleaned_data["username"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


# ==============================
# メールアドレス変更画面用
# ==============================

class EmailChangeForm(forms.ModelForm):
    email = forms.EmailField(
        label="メールアドレス",
        error_messages={
            "required": "メールアドレスを入力してください",
            "invalid": "メールアドレス形式で入力してください",
        },
    )

    class Meta:
        model = User
        fields = ["email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email:
            email = email.strip().lower()

        if email and User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスは既に登録されています")

        return email


# ==============================
# 名前変更画面用
# ==============================

class UsernameChangeForm(forms.ModelForm):
    username = forms.CharField(
        label="名前",
        error_messages={
            "required": "名前を入力してください",
        },
    )

    class Meta:
        model = User
        fields = ["username"]


# ==============================
# 日報フォーム
# ==============================

class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        exclude = ["report_date", "user"]


# ==============================
# ログインフォーム
# ==============================

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


# ==============================
# テンプレートフォーム
# ==============================

class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ["template1", "is_formal", "is_casual"]
        widgets = {
            "template1": forms.Textarea(
                attrs={
                    "class": "template-textarea",
                    "rows": 12,
                }
            ),
        }


# ==============================
# 予備：UserCreationForm版の新規登録フォーム
# 既存コードで SignupForm を参照している場合に備えて残す
# ==============================

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

        self.fields["username"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "ユーザー名を入力",
            }
        )

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "英語と数字を含む8文字以上で入力",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-input",
                "placeholder": "再度パスワードを入力",
            }
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email:
            email = email.strip().lower()

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("このメールアドレスはすでに登録されています。")

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = self.data.get(self.add_prefix("password1"), "")
        password2 = self.data.get(self.add_prefix("password2"), "")

        if password1 and not validate_password_rule(password1):
            add_error_once(
                self,
                "password1",
                PASSWORD_RULE_MESSAGE,
            )

        if password1 and password2 and password1 != password2:
            add_error_once(
                self,
                "password2",
                PASSWORD_MISMATCH_MESSAGE,
            )

        return cleaned_data


# ==============================
# パスワード再設定メール送信用フォーム
# ==============================

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
        error_messages={
            "required": "メールアドレスを入力してください",
            "invalid": "メールアドレス形式で入力してください",
        },
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()

        if email and not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "このメールアドレスは登録されていません。新規登録をおこなってください。"
            )

        return email

    def get_users(self, email):
        users = (
            User._default_manager
            .filter(email__iexact=email, is_active=True)
            .order_by("date_joined", "id")
        )

        for user in users:
            if user.has_usable_password():
                yield user
                return