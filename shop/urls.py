from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path("", views.index, name="index"),
    path("onboarding/", views.onboarding, name="onboarding"),
    path("complete-onboarding/", views.complete_onboarding, name="complete_onboarding"),
    path("register", views.register, name="register"),
    path("login", views.login_user, name="login"),
    path("women", views.women, name="women"),
    path("men", views.men, name="men"),
    path("search/", views.search, name="search"),
    path("featured/", views.featured_products, name="featured_products"),
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),
    path("product/<int:product_id>/review/", views.submit_review, name="submit_review"),
    path("cart", views.cart, name="cart"),
    path("add_to_cart", views.add_to_cart, name="add_to_cart"),
    path("update_cart", views.update_cart, name="update_cart"),
    path("remove_item", views.remove_item, name="remove_item"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="shop/password_reset_form.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="shop/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="shop/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="shop/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("mpesa/stk/<int:order_id>/", views.stk_push, name="stk_push"),
    path("mpesa/callback/", views.mpesa_callback, name="mpesa_callback"),
    path("check-order-status/", views.check_order_status, name="check_order_status"),
    path("inventory/", views.inventory, name="inventory"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("shipping_info/", views.shipping_info, name="shipping_info"),
    path("returns/", views.returns, name="returns"),
    path("logout/", views.logout_view, name="logout"),
    path("receipt/<int:order_id>/", views.receipt, name="receipt"),
    path(
        "receipt/<int:order_id>/download/",
        views.download_receipt_pdf,
        name="download_receipt_pdf",
    ),
    path("test-payment/<int:order_id>/", views.test_payment, name="test_payment"),
    path("update-shipping/", views.update_shipping, name="update_shipping"),
    path("my-receipts/", views.my_receipts, name="my_receipts"),
    path("order-history/", views.order_history, name="order_history"),
    path("delete-pending-order/<int:order_id>/", views.delete_pending_order, name="delete_pending_order"),
    path("reports/", views.reports, name="reports"),
    path("reports/generate/", views.generate_all_reports, name="generate_all_reports"),
    path("reports/<int:report_id>/", views.report_detail, name="report_detail"),
    path("track-order/", views.track_order, name="track_order"),
]
