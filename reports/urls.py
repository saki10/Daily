from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from reports.forms import LoginForm
from django.contrib.auth.views import LoginView
from reports.forms import LoginForm, CustomPasswordResetForm
from django.conf import settings
urlpatterns = [
    path('', views.report_list, name='home'),
    path('create/', views.report_create, name='create'),
    path('create/autosave/', views.report_autosave, name='report_autosave'),
    path('ai/generate/', views.ai_generate_report, name='ai_generate_report'),
    path('list/', views.report_list, name='report_list'),
    path('settings/', views.settings_view, name='settings'),
    path('signup/', views.signup, name='signup'),
    path('settings/email/', views.email_change, name='email_change'),
    path("history/", views.report_history, name="report_history"),

    path(
        "settings/password/",
        views.CustomPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "accounts/password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/accounts/reset/done/"
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("create/", views.report_create, name="create"),
    path('settings/username/', views.username_change, name='username_change'),
    path('ai/generate/', views.ai_generate_report, name='ai_generate_report'),
    path("integrations/", views.integrations, name="integrations"),
    path("integrations/slack/", views.slack_settings, name="slack_settings"),
    path("integrations/slack/post/", views.slack_post, name="slack_post"),
    path("integrations/teams/", views.teams_settings, name="teams_settings"),
    path("integrations/gmail/", views.gmail_settings, name="gmail_settings"),
    path("settings/slack/", views.slack_settings, name="slack_settings"),
    path("slack/post/", views.slack_post, name="slack_post"),
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    # パスワード再設定
    path(
    "accounts/password_reset/",
    views.CustomPasswordResetView.as_view(),
    name="password_reset",
    ),
]