from django.urls import path
# URLとビューをつなぐための機能を読み込む
from . import views
# 同じアプリの views.py を読み込む
from django.contrib.auth import views as auth_views


urlpatterns = [
     # トップ画面 = 日報一覧
    path('', views.report_list, name='home'),
     # 新規作成（＝AI生成もできる画面）
   path('create/', views.report_create, name='create'),
    # 日報一覧画面
    path('list/', views.report_list, name='report_list'),
    # 設定一覧画面
   path('settings/', views.settings_view, name='settings'),
   # 新規アカウント画面
   path('signup/', views.signup, name='signup'),
   # Email設定一覧画面
   path('settings/email/', views.email_change, name='email_change'),
   # PW設定一覧画面
  path(
      "settings/password/",
      auth_views.PasswordChangeView.as_view(
          template_name="reports/password_change_form.html",
          success_url="/settings/password/done/"
      ),
      name="password_change",
      ),
    path(
        "settings/password/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="reports/password_change_done.html"
        ),
        name="password_change_done",
    ),
   #username変更画面
   path('settings/username/', views.username_change, name='username_change'),
   #アカウント削除機能
   path('settings/delete/', views.account_delete, name='account_delete'), 
   #AI自動日記生成実装
   path('ai/generate/', views.ai_generate_report, name='ai_generate_report'),
   #外部連携画面
   path("integrations/", views.integrations, name="integrations"),
   path("integrations/slack/", views.slack_settings, name="slack_settings"),
   path("integrations/slack/post/", views.slack_post, name="slack_post"),
   path("integrations/teams/", views.teams_settings, name="teams_settings"),
   #テンプレート画面
   path("template/preview/", views.template_preview_api, name="template_preview_api"),
   path("template/", views.template_view, name="template"),
]
