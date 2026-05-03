import re
import json
import traceback
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from .models import DailyReport, UserIntegration
from .forms import DailyReportForm, SignupForm
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .utils import format_for_teams
from django.utils import timezone
from django.contrib.auth import login, get_user_model
from .forms import SignupForm
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth import get_user_model
from django.contrib.auth import login

SYSTEM_PROMPT = """
あなたは日本語の「業務日報」を作るアシスタントです。
ユーザーのメモを、読みやすい日報に整形してください。

【出力ルール】
- 出力は必ず JSON のみ（前後に説明文を付けない）
- JSONキーは必ず次の5つ：today_work, reflection, tomorrow_plan, note, warning
- 各値は文字列
- today_work / reflection / tomorrow_plan は箇条書き中心、具体的に
- 文体は、ユーザーが指定したトーン指示に従うこと
- 不明点は推測しすぎず「（要確認）」で補う
- warning には注意事項がなければ空文字を入れる
""".strip()

SLACK_WEBHOOK_RE = re.compile(
    r"^https://hooks\.slack\.com/services/[\w-]+/[\w-]+/[\w-]+$"
)


# =====================================
# 画面：日報作成（report_form）
# =====================================
def report_create(request):
    print("HIT report_create:", request.method)

    """
    日報作成画面
    - GET : ログイン済みなら今日の下書きがあれば復元
    - POST: ログイン済みのみ保存
    - 未ログイン: AI生成のみ利用可能
    """

    today = timezone.localdate()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(
                request,
                "日報の保存にはログインが必要です。AI生成のみご利用いただけます。"
            )
            return redirect("home")

        form = DailyReportForm(request.POST)
        print("POST received")

        if form.is_valid():
            print("FORM valid")

            report, created = DailyReport.objects.get_or_create(
                user=request.user,
                report_date=today
            )

            report.ai_memo = request.POST.get("ai_memo", "").strip()
            report.today_work = form.cleaned_data["today_work"]
            report.reflection = form.cleaned_data["reflection"]
            report.tomorrow_plan = form.cleaned_data["tomorrow_plan"]
            report.note = form.cleaned_data["note"]
            report.is_draft = False
            report.save()

            print("REPORT saved:", report.id, report.report_date)

            integration, _ = UserIntegration.objects.get_or_create(user=request.user)

            print("=== integration debug ===")
            print("user:", request.user)
            print("slack_enabled:", integration.slack_enabled)
            print("slack_webhook_url:", integration.slack_webhook_url)
            print("teams_enabled:", integration.teams_enabled)
            print("teams_webhook_url:", integration.teams_webhook_url)
            print("gmail_enabled:", integration.gmail_enabled)
            print("gmail_email:", integration.gmail_email)

            slack_text = (
                f"【日報】{report.report_date}\n\n"
                f"■ 今日やったこと\n{report.today_work}\n\n"
                f"■ 振り返り\n{report.reflection}\n\n"
                f"■ 明日の予定\n{report.tomorrow_plan}\n\n"
                f"■ 備考\n{report.note}"
            )

            today_work = format_for_teams(report.today_work)
            reflection = format_for_teams(report.reflection)
            tomorrow_plan = format_for_teams(report.tomorrow_plan)
            note = format_for_teams(report.note)

            teams_text = (
                f"【日報】{report.report_date}\n\n"
                "**■ 今日やったこと**\n\n"
                f"{today_work}\n\n"
                "**■ 振り返り**\n\n"
                f"{reflection}\n\n"
                "**■ 明日の予定**\n\n"
                f"{tomorrow_plan}\n\n"
                "**■ 備考**\n\n"
                f"{note}"
            )

            if integration.slack_enabled and integration.slack_webhook_url:
                print("Slack send start")
                ok, error = send_slack_webhook(
                    integration.slack_webhook_url,
                    slack_text
                )
                print("Slack send result:", ok, error)

                if not ok:
                    messages.error(request, f"Slack送信に失敗しました: {error}")
            else:
                print("Slack skipped")

            if integration.teams_enabled and integration.teams_webhook_url:
                print("Teams send start")
                ok, error = send_teams_webhook(
                    integration.teams_webhook_url,
                    teams_text
                )
                print("Teams send result:", ok, error)

                if not ok:
                    messages.error(request, f"Teams送信に失敗しました: {error}")
            else:
                print("Teams skipped")

            if integration.gmail_enabled and integration.gmail_email:
                print("Gmail send start")
                try:
                    gmail_body = (
                        f"【日報】{report.report_date}\n\n"
                        f"■ 今日やったこと\n{report.today_work}\n\n"
                        f"■ 振り返り\n{report.reflection}\n\n"
                        f"■ 明日の予定\n{report.tomorrow_plan}\n\n"
                        f"■ 備考\n{report.note}"
                    )

                    send_mail(
                        "Daily 日報",
                        gmail_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [integration.gmail_email],
                        fail_silently=False,
                    )
                    print("Gmail send success")
                except Exception as e:
                    print("Gmail send error:", e)
                    messages.error(request, f"Gmail送信に失敗しました: {e}")
            elif integration.gmail_enabled and not integration.gmail_email:
                print("Gmail skipped: no gmail_email")
                messages.error(request, "Gmail送信先のメールアドレスが未設定です")
            else:
                print("Gmail skipped")

            messages.success(request, "日報を保存しました")
            return redirect("create")

        else:
            print("FORM invalid:", form.errors)

        return render(request, "reports/report_form.html", {
            "form": form,
            "ai_memo": request.POST.get("ai_memo", ""),
        })

    if request.user.is_authenticated:
        report = DailyReport.objects.filter(
            user=request.user,
            report_date=today
        ).first()

        if report:
            form = DailyReportForm(instance=report)
            ai_memo = report.ai_memo
        else:
            form = DailyReportForm()
            ai_memo = ""
    else:
        form = DailyReportForm()
        ai_memo = ""

    return render(request, "reports/report_form.html", {
        "form": form,
        "ai_memo": ai_memo,
    })
# =====================================
# 画面：自動保存
# =====================================
@login_required
@require_POST
def report_autosave(request):
    """
    create画面の入力内容を下書き保存する
    ここでは外部連携は送らない
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
        today = timezone.localdate()

        report, created = DailyReport.objects.get_or_create(
            user=request.user,
            report_date=today
        )

        report.ai_memo = (body.get("ai_memo") or "").strip()
        report.today_work = (body.get("today_work") or "").strip()
        report.reflection = (body.get("reflection") or "").strip()
        report.tomorrow_plan = (body.get("tomorrow_plan") or "").strip()
        report.note = (body.get("note") or "").strip()
        report.is_draft = True
        report.save()

        return JsonResponse({
            "ok": True,
            "saved_at": timezone.localtime().strftime("%H:%M:%S")
        })

    except Exception as e:
        print("report_autosave error:", e)
        return JsonResponse({
            "ok": False,
            "error": str(e)
        }, status=500)


# =====================================
# 画面：ホーム
# =====================================
@login_required
def home(request):
    latest_reports = DailyReport.objects.filter(
        user=request.user
    ).order_by("-report_date", "-id")[:3]

    context = {
        "latest_reports": latest_reports,
    }
    return render(request, "reports/home.html", context)


# =====================================
# 画面：日報一覧（検索付き）
# =====================================
@login_required
def report_list(request):
    q = request.GET.get("q", "").strip()

    reports = DailyReport.objects.filter(
        user=request.user
    ).order_by("-report_date", "-id")

    if q:
        reports = reports.filter(
            Q(today_work__icontains=q) |
            Q(reflection__icontains=q) |
            Q(tomorrow_plan__icontains=q) |
            Q(note__icontains=q)
        )

    context = {
        "reports": reports,
        "q": q,
        "result_count": reports.count(),
    }
    return render(request, "reports/report_list.html", context)


# =====================================
# 画面：設定
# =====================================
@login_required
def settings_view(request):
    return render(request, "reports/settings.html")


# =====================================
# 画面：日報履歴
# =====================================
@login_required
def report_history(request):
    reports = DailyReport.objects.filter(
        user=request.user
    ).order_by("-report_date", "-id")

    context = {
        "reports": reports,
        "result_count": reports.count(),
    }
    return render(request, "reports/report_history.html", context)


# =====================================
# 設定：メール変更
# =====================================
@login_required
def email_change(request):
    """
    メールアドレス変更
    - POST: 入力された email を現在のユーザーに設定する
    """
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()

        if not email:
            messages.error(request, "新しいメールアドレスを入力してください。")
            return redirect("email_change")

        UserModel = get_user_model()

        if UserModel.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            messages.error(request, "このメールアドレスはすでに登録されています。")
            return redirect("email_change")

        request.user.email = email
        request.user.save()

        messages.success(request, "メールアドレスを変更しました。")
        return redirect("settings")

    return render(request, "reports/email_change.html")

# =====================================
# 設定：ユーザー名変更
# =====================================
@login_required
def username_change(request):
    """
    ユーザーネーム変更
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "ユーザーネームを入力してください。")
            return redirect("username_change")

        UserModel = get_user_model()

        if UserModel.objects.filter(username=username).exclude(pk=request.user.pk).exists():
            messages.error(request, "このユーザーネームはすでに使用されています。")
            return redirect("username_change")

        request.user.username = username
        request.user.save()

        messages.success(request, "ユーザーネームを変更しました。")
        return redirect("settings")

    return render(request, "reports/username_change.html")

# =====================================
# 設定：パスワード変更
# =====================================
@login_required
def password_change(request):
    """
    パスワード変更
    - PasswordChangeForm を使用
    - update_session_auth_hash でログイン維持
    """
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "パスワードを変更しました")
            return redirect("settings")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "reports/password_change_form.html", {"form": form})


# =====================================
# アカウント：新規登録
# =====================================
def signup(request):
    """
    新規登録
    - 登録完了後、自動ログインしてホーム画面へ遷移
    """
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "新規登録が完了しました。")
            return redirect("home")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})

# =====================================
# AI：日報生成 API
# =====================================
@require_POST
def ai_generate_report(request):
    try:
        from openai import OpenAI

        body = json.loads(request.body.decode("utf-8"))
        user_prompt = (body.get("prompt") or "").strip()
        tone = (body.get("tone") or "formal").strip().lower()

        if not user_prompt:
            return JsonResponse({"error": "素材入力を入力してください"}, status=400)

        if tone == "casual":
            tone_instruction = (
                "やや親しみやすい自然な文体で書いてください。"
                "ただし、業務日報として読めるように砕けすぎない表現にしてください。"
            )
        else:
            tone_instruction = (
                "丁寧でかしこまったフォーマルな文体（です・ます調）で書いてください。"
            )

        prompt = f"""
以下の素材をもとに、日本語の業務日報を作成してください。

【文体】
{tone_instruction}

【素材】
{user_prompt}

必ず次のJSONオブジェクトのみを返してください。
説明文やコードブロックは不要です。

{{
  "today_work": "",
  "reflection": "",
  "tomorrow_plan": "",
  "note": "",
  "warning": ""
}}
""".strip()

        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        SYSTEM_PROMPT
                        + "\n出力は必ずJSONオブジェクトのみで返してください。"
                        + "\nキーは today_work, reflection, tomorrow_plan, note, warning のみ使用してください。"
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={"type": "json_object"},
        )

        raw_text = (completion.choices[0].message.content or "").strip()
        print("OpenAI raw_text:", raw_text)

        if not raw_text:
            return JsonResponse(
                {"error": "AIの返却結果が空でした。モデル応答を確認してください。"},
                status=500
            )

        result = json.loads(raw_text)

        return JsonResponse({
            "today_work": result.get("today_work", ""),
            "reflection": result.get("reflection", ""),
            "tomorrow_plan": result.get("tomorrow_plan", ""),
            "note": result.get("note", ""),
            "warning": result.get("warning", ""),
        })

    except json.JSONDecodeError as e:
        traceback.print_exc()
        return JsonResponse({"error": f"JSON解析エラー: {str(e)}"}, status=500)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"{type(e).__name__}: {str(e)}"}, status=500)

# =====================================
# Slack設定
# =====================================
@login_required
@require_POST
def slack_post(request):
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "text が空です"}, status=400)

    setting, _ = UserIntegration.objects.get_or_create(user=request.user)

    if not getattr(setting, "slack_enabled", False):
        return JsonResponse({"ok": False, "error": "Slack連携がOFFです"}, status=400)

    webhook_url = (getattr(setting, "slack_webhook_url", "") or "").strip()
    if not webhook_url:
        return JsonResponse({"ok": False, "error": "Webhook URLが未設定です"}, status=400)

    if not SLACK_WEBHOOK_RE.match(webhook_url):
        return JsonResponse({"ok": False, "error": "Webhook URLの形式が不正です"}, status=400)

    try:
        r = requests.post(webhook_url, json={"text": text}, timeout=10)
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": f"Slack通信エラー: {e}"}, status=502)

    if r.status_code == 200:
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False, "error": r.text}, status=400)


# =====================================
# Teams設定
# =====================================
@login_required
@require_POST
def teams_post(request):
    text = request.POST.get("text", "").strip()

    if not text:
        return JsonResponse({"ok": False, "error": "text が空です"}, status=400)

    setting, _ = UserIntegration.objects.get_or_create(user=request.user)

    if not setting.teams_enabled:
        return JsonResponse({"ok": False, "error": "Teams連携がOFFです"}, status=400)

    if not setting.teams_webhook_url:
        return JsonResponse({"ok": False, "error": "Teams Webhook URLが未設定です"}, status=400)

    ok, error = send_teams_webhook(setting.teams_webhook_url, text)

    if ok:
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False, "error": error}, status=400)


# =====================================
# 外部連携設定（ON/OFF）
# =====================================
@login_required
def integrations(request):
    """外部連携設定（Slack/Teams/GmailのON/OFFを保存）"""
    integration, _ = UserIntegration.objects.get_or_create(user=request.user)

    if request.method == "POST":
        integration.slack_enabled = ("slack" in request.POST)
        integration.teams_enabled = ("teams" in request.POST)
        integration.gmail_enabled = ("gmail" in request.POST)

        if integration.slack_enabled and not integration.slack_webhook_url:
            integration.slack_enabled = False
            messages.warning(request, "SlackをONにするにはWebhook URLの設定が必要です")

        if integration.teams_enabled and not integration.teams_webhook_url:
            integration.teams_enabled = False
            messages.warning(request, "TeamsをONにするにはWebhook URLの設定が必要です")

        if integration.gmail_enabled and not integration.gmail_email:
            integration.gmail_enabled = False
            messages.warning(
                request,
                "GmailをONにするにはGmail設定画面で送付先メールアドレスの登録が必要です"
            )

        integration.save()
        messages.success(request, "外部連携設定を保存しました")
        return redirect("integrations")

    return render(request, "reports/integrations.html", {"integration": integration})
# =====================================
# Slack設定（Webhook URL 保存）
# =====================================
@login_required
def slack_settings(request):
    """Slack設定画面：Incoming Webhook URL を保存する"""
    integration, _ = UserIntegration.objects.get_or_create(user=request.user)

    if request.method == "POST":
        url = (request.POST.get("slack_webhook_url") or "").strip()

        if url and not SLACK_WEBHOOK_RE.match(url):
            messages.error(request, "Webhook URLの形式が正しくありません")
            return redirect("slack_settings")

        integration.slack_webhook_url = url
        integration.save()
        messages.success(request, "Slack Webhook URLを保存しました")
        return redirect("integrations")

    return render(request, "reports/slack_settings.html", {"integration": integration})


# =====================================
# Teams設定（Webhook URL 保存）
# =====================================
@login_required
def teams_settings(request):
    integration, _ = UserIntegration.objects.get_or_create(user=request.user)

    if request.method == "POST":
        integration.teams_webhook_url = (request.POST.get("teams_webhook_url") or "").strip()
        integration.save()
        messages.success(request, "Teams設定を保存しました")
        return redirect("teams_settings")

    return render(
        request,
        "reports/teams_settings.html",
        {"integration": integration}
    )


# =====================================
# Slack通知（Webhook送信）
# =====================================
def send_slack_webhook(webhook_url: str, text: str) -> tuple[bool, str]:
    """Slack Incoming Webhook にメッセージを投稿する"""
    try:
        r = requests.post(webhook_url, json={"text": text}, timeout=10)
        print("Slack status code:", r.status_code)
        print("Slack response text:", r.text)

        if 200 <= r.status_code < 300:
            return True, ""

        return False, f"Slack通知失敗（status={r.status_code} body={r.text}）"

    except Exception as e:
        print("Slack send error:", e)
        return False, f"Slack通知例外: {e}"


# =====================================
# Teams通知（Webhook送信）
# =====================================
def send_teams_webhook(webhook_url: str, text: str) -> tuple[bool, str]:
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": text,
                            "wrap": True
                        }
                    ]
                }
            }
        ]
    }

    try:
        r = requests.post(webhook_url, json=payload, timeout=10)

        if r.status_code in [200, 202]:
            return True, ""

        return False, f"status={r.status_code} body={r.text}"

    except Exception as e:
        return False, str(e)


# =====================================
# Gmail通知（メール送信）
# =====================================
def send_gmail(text, to_email):
    send_mail(
    "Daily 日報",
    body,
    settings.DEFAULT_FROM_EMAIL,
    [integration.gmail_email],
    fail_silently=False,
    )

# =====================================
# 画面：Gmail設定
# =====================================
@login_required
def gmail_settings(request):
    integration, _ = UserIntegration.objects.get_or_create(user=request.user)

    if request.method == "POST":
        gmail_email = request.POST.get("gmail_email", "").strip()
        action = request.POST.get("action")

        if not gmail_email:
            messages.error(request, "送付先のGmailアドレスを入力してください。")
            return render(
                request,
                "reports/gmail_settings.html",
                {"integration": integration}
            )

        integration.gmail_email = gmail_email

        if action == "save":
            integration.gmail_enabled = True
            integration.save()
            messages.success(request, "Gmail設定を保存しました。")
            return redirect("gmail_settings")

        if action == "test":
            integration.save()
            try:
                send_mail(
                    "【テスト送信】Daily Gmail連携",
                    "DailyアプリからGmailへテスト送信できています。",
                    settings.DEFAULT_FROM_EMAIL,
                    [integration.gmail_email],
                    fail_silently=False,
                )
                messages.success(request, "テストメールを送信しました。")
            except Exception as e:
                messages.error(request, f"Gmail送信に失敗しました: {e}")

            return redirect("gmail_settings")

    return render(
        request,
        "reports/gmail_settings.html",
        {"integration": integration}
    )

# =====================================
# PW変更完了画面
# =====================================
class CustomPasswordChangeView(PasswordChangeView):
    template_name = "reports/password_change_form.html"
    success_url = reverse_lazy("settings")

    def form_valid(self, form):
        messages.success(self.request, "パスワードを変更しました。")
        return super().form_valid(form)