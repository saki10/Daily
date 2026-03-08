import re
import json
import traceback

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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
""".strip()

SLACK_WEBHOOK_RE = re.compile(r"^https://hooks\.slack\.com/services/[\w-]+/[\w-]+/[\w-]+$")



# =====================================
# Gmail送信
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
# 画面：日報作成（report_form）
# =====================================
@login_required
def report_create(request):
    print("HIT report_create:", request.method)

    """
    日報作成画面
    - GET : 空フォーム表示
    - POST: 入力を保存 → Slack/Teams/Gmail通知 → 同じ画面へリダイレクト
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
            # Slack用テキスト
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
                "**■ 今日やったこと**\n\n"
                f"{today_work}\n\n"
                "**■ 振り返り**\n\n"
                f"{reflection}\n\n"
                "**■ 明日の予定**\n\n"
                f"{tomorrow_plan}\n\n"
                "**■ 備考**\n\n"
                f"{note}"
            )

            # =====================
            # Gmail用テキスト
            # =====================
            gmail_text = (
                f"【日報】{report.report_date}\n\n"
                f"■ 今日やったこと\n{report.today_work}\n\n"
                f"■ 振り返り\n{report.reflection}\n\n"
                f"■ 明日の予定\n{report.tomorrow_plan}\n\n"
                f"■ 備考\n{report.note}"
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

            # =====================
            # Gmail送信
            # =====================
            if integration.gmail_enabled and request.user.email:
                send_gmail(gmail_text, request.user.email)
                messages.success(request, "Gmailへ送信しました")

            return redirect("create")

        else:
            print("FORM invalid:", form.errors)

    else:
        form = DailyReportForm()

    return render(request, "reports/report_form.html", {"form": form})
# =====================================
# 画面：日報一覧（検索付き）
# =====================================
@login_required
def report_list(request):
    """
    日報一覧（検索機能付き）
    - q があれば today_work / reflection / note に部分一致検索
    """
    q = request.GET.get("q", "").strip()

    reports = DailyReport.objects.all().order_by("-id")

    if q:
        reports = reports.filter(
            Q(today_work__icontains=q) |
            Q(reflection__icontains=q) |
            Q(note__icontains=q)
        )

    return render(request, "reports/report_list.html", {"reports": reports, "q": q})


# =====================================
# 画面：設定トップ
# =====================================
@login_required
def settings_view(request):
    """設定画面トップ"""
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

    return render(request, "reports/password_change.html", {"form": form})


# =====================================
# アカウント：新規登録
# =====================================
def signup(request):
    """
    新規登録
    - SignupForm の password / password_confirm を利用
    """
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            login(request, user)
            return redirect("report_list")
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

client = OpenAI()  # 環境変数 OPENAI_API_KEY を使用
@csrf_exempt
def ai_generate_report(request):
    """
    AI日報生成（フロントから JSON を受け取り、JSONで返す）

    受け取り:
      { "prompt": "..."} または { "user_prompt": "..."} または { "memo": "..." }

    返却（成功時）:
      {
        "today_work": "...",
        "reflection": "...",
        "tomorrow_plan": "...",
        "note": "..."
      }
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    # --- リクエストJSONの取得 ---
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # フロント側のキー揺れ対策（prompt / user_prompt / memo のどれでも受ける）
    memo = (payload.get("prompt") or payload.get("user_prompt") or payload.get("memo") or "").strip()
    if not memo:
        return JsonResponse({"error": "prompt is empty"}, status=400)

    # --- OpenAI呼び出し ---
    try:
        user_prompt = f"""
次のメモをもとに日報を作成してください。

【メモ】
{memo}

【出力形式】（この形式で、JSONのみ出力）
{{
  "today_work": "・〜\\n・〜",
  "reflection": "・〜\\n・〜",
  "tomorrow_plan": "・〜\\n・〜",
  "note": "・〜"
}}
"""

        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.6,
        )

        content = resp.choices[0].message.content.strip()

        # AIの返答がJSONである前提でパース
        data = json.loads(content)

        result = {
            "today_work": str(data.get("today_work", "")).strip(),
            "reflection": str(data.get("reflection", "")).strip(),
            "tomorrow_plan": str(data.get("tomorrow_plan", "")).strip(),
            "note": str(data.get("note", "")).strip(),
        }

        # 最低限の保険（空ならユーザーに追記を促す）
        if not result["today_work"]:
            result["today_work"] = "・（要確認）本日の作業内容を追記してください"
        if not result["tomorrow_plan"]:
            result["tomorrow_plan"] = "・（要確認）明日の予定を追記してください"

        return JsonResponse(result, status=200)

    except json.JSONDecodeError:
        # AIの返答がJSONではない場合
        return JsonResponse(
            {"error": "AIの返答がJSONになっていない可能性があります"},
            status=400
        )

    except Exception as e:
        # Quota/429 の場合はダミー文章を返す（開発中の確認用）
        msg = str(e)
        if "insufficient_quota" in msg or "Error code: 429" in msg:
            return JsonResponse({
                "today_work": "・（ダミー）会議資料作成\n・（ダミー）バグ修正\n・（ダミー）顧客対応",
                "reflection": "・（ダミー）優先順位付けを改善すると効率が上がりそうです",
                "tomorrow_plan": "・（ダミー）テスト実施\n・（ダミー）仕様確認",
                "note": "（ダミー）API利用枠がないためダミー文章を返しています",
                "warning": "insufficient_quota"
            }, status=200)

        return JsonResponse({
            "error": msg,
            "traceback": traceback.format_exc(),
        }, status=500)
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
# テンプレート画面
# =====================================
client = OpenAI(api_key=settings.OPENAI_API_KEY)
print("OPENAI_API_KEY exists =", bool(settings.OPENAI_API_KEY))
@login_required
@require_POST
@login_required
@require_POST
def template_preview_api(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        text = data.get("text", "").strip()
        style = data.get("style", "formal")

        if not text:
            return JsonResponse({"preview_text": ""})

        style_instruction = {
            "formal": "以下の文章を日本語の自然なビジネス向けの丁寧語に整えてください。意味は変えず、箇条書きや改行は可能な限り維持してください。",
            "casual": "以下の文章を日本語の自然でややくだけた表現に整えてください。意味は変えず、箇条書きや改行は可能な限り維持してください。",
        }.get(style, "以下の文章を自然な日本語に整えてください。")

        response = client.responses.create(
            model="gpt-5.4",
            input=f"{style_instruction}\n\n{text}"
        )

        return JsonResponse({"preview_text": response.output_text})

    except Exception as e:
        msg = str(e)

        # API利用枠不足時は画面確認用にフォールバック
        if "insufficient_quota" in msg or "Error code: 429" in msg:
            preview_text = text

            if style == "formal":
                preview_text = text.replace("やったこと", "実施した内容")
            elif style == "casual":
                preview_text = text.replace("今日は", "今日").replace("実施した内容", "やったこと")

            return JsonResponse({
                "preview_text": preview_text,
                "warning": "OpenAI APIの利用枠不足のため簡易プレビューを返しています"
            }, status=200)

        import traceback
        return JsonResponse({
            "error": msg,
            "traceback": traceback.format_exc(),
        }, status=500)


@login_required
def template_view(request):
    if request.method == "POST":
        saved_template1 = request.POST.get("template_text", "")
        saved_tone = request.POST.get("tone", "formal")

        request.session["saved_template1"] = saved_template1
        request.session["saved_tone"] = saved_tone

        messages.success(request, "テンプレートを保存しました")
        return redirect("template")

    saved_template1 = request.session.get(
        "saved_template1",
        "今日はやったこと\n・（ダミー）会議資料作成\n・（ダミー）バグ修正\n・（ダミー）顧客対応"
    )
    saved_tone = request.session.get("saved_tone", "formal")

    return render(request, "reports/template.html", {
        "saved_template1": saved_template1,
        "saved_tone": saved_tone,
    })