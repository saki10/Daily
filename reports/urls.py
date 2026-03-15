from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.report_list, name='home'),
    path('create/', views.report_create, name='create'),
    path('list/', views.report_list, name='report_list'),
    path('settings/', views.settings_view, name='settings'),
    path('signup/', views.signup, name='signup'),
    path('settings/email/', views.email_change, name='email_change'),

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

    path(
        "accounts/password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url="/accounts/password_reset/done/",
        ),
        name="password_reset",
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

    path('settings/username/', views.username_change, name='username_change'),
    path('settings/delete/', views.account_delete, name='account_delete'),
    path('ai/generate/', views.ai_generate_report, name='ai_generate_report'),
    path("integrations/", views.integrations, name="integrations"),
    path("integrations/slack/", views.slack_settings, name="slack_settings"),
    path("integrations/slack/post/", views.slack_post, name="slack_post"),
    path("integrations/teams/", views.teams_settings, name="teams_settings"),
    # path("template/preview/", views.template_preview_api, name="template_preview_api"),
    # path("template/", views.template_view, name="template"),

]