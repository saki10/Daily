import re
import json
import requests
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from openai import OpenAI
from .models import DailyReport, UserIntegration
from .forms import DailyReportForm, SignupForm
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import UserIntegration
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .utils import send_teams_webhook, format_for_teams


client = OpenAI()  # 環境変数 OPENAI_API_KEY を使用

SYSTEM_PROMPT = """
あなたは日本語の「業務日報」を作るアシスタントです。
ユーザーのメモを、読みやすい日報に整形してください。

【出力ルール】
- 出力は必ず JSON のみ（前後に説明文を付けない）
- JSONキーは必ず次の4つ：today_work, reflection, tomorrow_plan, note
- 各値は文字列
- today_work / reflection / tomorrow_plan は箇条書き中心、具体的に
- 文体は、ユーザーが指定したトーン指示に従うこと
- 不明点は推測しすぎず「（要確認）」で補う
""".strip()

SLACK_WEBHOOK_RE = re.compile(r"^https://hooks\.slack\.com/services/[\w-]+/[\w-]+/[\w-]+$")



# =====================================
# 画面：日報作成（report_form）
# =====================================
@login_required
def report_create(request):
    print("HIT report_create:", request.method)

    """
    日報作成画面
    - GET : 空フォーム表示
    - POST: 入力を保存 → Slack/Teams通知 → 同じ画面へリダイレクト
    """

    if request.method == "POST":
        form = DailyReportForm(request.POST)
        print("POST received")

        if form.is_valid():
            print("FORM valid")

            # ① 保存（同じ日付なら更新）
            report_date = form.instance.report_date
            report, created = DailyReport.objects.get_or_create(
                user=request.user,
                report_date=report_date
            )

            report.today_work = form.cleaned_data["today_work"]
            report.reflection = form.cleaned_data["reflection"]
            report.tomorrow_plan = form.cleaned_data["tomorrow_plan"]
            report.note = form.cleaned_data["note"]

            report.save()

            # ② 連携設定取得
            integration, _ = UserIntegration.objects.get_or_create(user=request.user)

            # =====================
            # Slack用テキスト（整形なし）
            # =====================
            slack_text = (
                f"【日報】{report.report_date}\n\n"
                f"今日やったこと\n{report.today_work}\n\n"
                f"振り返り\n{report.reflection}\n\n"
                f"明日の予定\n{report.tomorrow_plan}\n\n"
                f"備考\n{report.note}"
            )

            # =====================
            # Teams用整形
            # =====================
            today_work = format_for_teams(report.today_work)
            reflection = format_for_teams(report.reflection)
            tomorrow_plan = format_for_teams(report.tomorrow_plan)
            note = format_for_teams(report.note)

            teams_text = (
            f"【日報】{report.report_date}\n\n"

            "**■ 今日やったこと**\n\n\n"
            f"{today_work}\n\n"

            "**■ 振り返り**\n\n"
            f"{reflection}\n\n"

            "**■ 明日の予定**\n\n"
            f"{tomorrow_plan}\n\n"

            "**■ 備考**\n\n"
            f"{note}"
        )

            # =====================
            # Slack送信
            # =====================
            if integration.slack_enabled and integration.slack_webhook_url:
                send_slack_webhook(integration.slack_webhook_url, slack_text)

            # =====================
            # Teams送信
            # =====================
            if integration.teams_enabled and integration.teams_webhook_url:
                send_teams_webhook(integration.teams_webhook_url, teams_text)

            return redirect("create")

        else:
            print("FORM invalid:", form.errors)

    else:
        form = DailyReportForm()

    return render(request, "reports/report_form.html", {"form": form})
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from .models import DailyReport


# =====================================
# 画面：ホーム
# =====================================
@login_required
def home(request):
    latest_reports = DailyReport.objects.filter(user=request.user).order_by("-report_date", "-id")[:3]

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

    reports = DailyReport.objects.filter(user=request.user).order_by("-report_date", "-id")

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
def settings_view(request):
    return render(request, "reports/settings.html")

# =====================================
# 設定：メール変更
# =====================================
@login_required
def email_change(request):
    """
    メールアドレス変更
    - POST: email / email_confirm が一致すれば更新
    """
    if request.method == "POST":
        email = request.POST.get("email", "")
        email_confirm = request.POST.get("email_confirm", "")

        if email != email_confirm:
            messages.error(request, "メールアドレスが一致しません")
            return redirect("email_change")

        request.user.email = email
        request.user.save()
        messages.success(request, "メールアドレスを変更しました")
        return redirect("settings")

    return render(request, "reports/email_change.html")


# =====================================
# 設定：ユーザー名変更
# =====================================
@login_required
def username_change(request):
    """
    ユーザー名変更
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "ユーザー名を入力してください")
            return redirect("username_change")

        request.user.username = username
        request.user.save()
        messages.success(request, "ユーザー名を変更しました")
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

    return render(request, "templates/registration/signup.html", {"form": form})


# =====================================
# アカウント：新規登録
# =====================================
def signup(request):
    """
    新規登録
    - SignupForm（UserCreationForm継承）を利用
    """
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "新規登録が完了しました。ログインしてください。")
            return redirect("login")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})
# =====================================
# アカウント：削除
# =====================================
@login_required
def account_delete(request):
    """
    アカウント削除
    - POST: ログアウトしてから削除
    """
    if request.method == "POST":
        user = request.user
        logout(request)
        user.delete()
        return redirect("login")

    return render(request, "reports/account_delete.html")


# =====================================
# AI：日報生成 API
# =====================================
SYSTEM_PROMPT = """
あなたは日本語の「業務日報」を作るアシスタントです。
ユーザーのメモを、読みやすい日報に整形してください。

【出力ルール】
- 出力は必ず JSON のみ（前後に説明文を付けない）
- JSONキーは必ず次の4つ：today_work, reflection, tomorrow_plan, note
- 各値は文字列
- today_work / reflection / tomorrow_plan は箇条書き中心、具体的に
- 文体は丁寧語（です/ます）で統一
- 不明点は推測しすぎず「（要確認）」で補う
"""
# Slack Incoming Webhook URLの簡易バリデーション
SLACK_WEBHOOK_RE = re.compile(r"^https://hooks\.slack\.com/services/[\w-]+/[\w-]+/[\w-]+$")

@require_POST
def ai_generate_report(request):
    try:
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
""".strip()

        response = client.responses.create(
            model="gpt-4.1-mini",
            instructions=SYSTEM_PROMPT,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "daily_report",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "today_work": {"type": "string"},
                            "reflection": {"type": "string"},
                            "tomorrow_plan": {"type": "string"},
                            "note": {"type": "string"},
                            "warning": {"type": "string"}
                        },
                        "required": [
                            "today_work",
                            "reflection",
                            "tomorrow_plan",
                            "note"
                        ],
                        "additionalProperties": False
                    }
                }
            }
        )

        result = json.loads(response.output_text)

        return JsonResponse({
            "today_work": result.get("today_work", ""),
            "reflection": result.get("reflection", ""),
            "tomorrow_plan": result.get("tomorrow_plan", ""),
            "note": result.get("note", ""),
            "warning": result.get("warning", ""),
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "リクエスト形式が不正です"}, status=400)

    except Exception as e:
        print("ai_generate_report error:", e)
        return JsonResponse({"error": "AI生成に失敗しました"}, status=500)
# =====================================
# Slack設定
# =====================================
@login_required
@require_POST
def slack_post(request):
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "text が空です"}, status=400)

    # 設定が無い場合も落ちないように
    setting, _ = UserIntegration.objects.get_or_create(user=request.user)

    if not getattr(setting, "slack_enabled", False):
        return JsonResponse({"ok": False, "error": "Slack連携がOFFです"}, status=400)

    webhook_url = (getattr(setting, "slack_webhook_url", "") or "").strip()
    if not webhook_url:
        return JsonResponse({"ok": False, "error": "Webhook URLが未設定です"}, status=400)

    # ✅ ここで簡易バリデーションを使う（定義したなら使う）
    if not SLACK_WEBHOOK_RE.match(webhook_url):
        return JsonResponse({"ok": False, "error": "Webhook URLの形式が不正です"}, status=400)

    try:
        r = requests.post(webhook_url, json={"text": text}, timeout=10)
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": f"Slack通信エラー: {e}"}, status=502)

    if r.status_code == 200:
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False, "error": r.text}, status=400)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "text が空です"}, status=400)

    # 🔽 ここはあなたのSlack設定保存モデルに合わせる
    setting = IntegrationSetting.objects.get(user=request.user)

    if not setting.slack_enabled:
        return JsonResponse({"ok": False, "error": "Slack連携がOFFです"}, status=400)

    if not setting.slack_webhook_url:
        return JsonResponse({"ok": False, "error": "Webhook URLが未設定です"}, status=400)

    r = requests.post(setting.slack_webhook_url, json={"text": text}, timeout=10)

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

    setting = UserIntegration.objects.get(user=request.user)

    if not setting.teams_enabled:
        return JsonResponse({"ok": False, "error": "Teams連携がOFFです"}, status=400)

    if not setting.teams_webhook_url:
        return JsonResponse({"ok": False, "error": "Teams Webhook URLが未設定です"}, status=400)

    try:
        r = requests.post(
            setting.teams_webhook_url,
            json={"text": text},
            timeout=10
        )
    except requests.RequestException as e:
        return JsonResponse({"ok": False, "error": f"Teams通信エラー: {e}"}, status=502)

    if r.status_code == 200:
        return JsonResponse({"ok": True})

    return JsonResponse({"ok": False, "error": r.text}, status=400)
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

        # 任意：SlackをONにしたのにWebhook未設定なら注意を出す
        if integration.slack_enabled and not integration.slack_webhook_url:
            messages.warning(request, "SlackをONにするにはWebhook URLの設定が必要です")

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

        # 空はOK（未設定に戻したいケース）
        if url and not SLACK_WEBHOOK_RE.match(url):
            messages.error(request, "Webhook URLの形式が正しくありません")
            return redirect("slack_settings")

        integration.slack_webhook_url = url
        integration.save()
        messages.success(request, "Slack Webhook URLを保存しました")
        return redirect("integrations")

    return render(request, "reports/slack_settings.html", {"integration": integration})

# =====================================
# Googlemeet設定（Webhook URL 保存）
# =====================================

@login_required
def teams_settings(request):

    integration, _ = UserIntegration.objects.get_or_create(user=request.user)

    if request.method == "POST":
        integration.teams_webhook_url = request.POST.get("teams_webhook_url")
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
        r = requests.post(webhook_url, json={"text": text}, timeout=5)
        if 200 <= r.status_code < 300:
            return True, ""
        return False, f"Slack通知失敗（status={r.status_code}）"
    except Exception as e:
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
        r = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        if 200 <= r.status_code < 300:
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
        text,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )
    
# =====================================
# Teams通知（メール送信）
# =====================================



