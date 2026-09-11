from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BudgetViewSet,
    CategoryViewSet,
    ExpenseViewSet,
    FinanceLessonViewSet,
    MeView,
    OnboardingView,
    ProfileView,
    RegisterView,
    confirm_password_reset,
    request_password_reset,
    reset_pin,
    set_pin,
    summary,
    verify_pin,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("budgets", BudgetViewSet, basename="budget")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("lessons", FinanceLessonViewSet, basename="lesson")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/password-reset/", request_password_reset, name="password-reset"),
    path("auth/password-reset/confirm/", confirm_password_reset, name="password-reset-confirm"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("pin/set/", set_pin, name="pin-set"),
    path("pin/verify/", verify_pin, name="pin-verify"),
    path("pin/reset/", reset_pin, name="pin-reset"),
    path("summary/", summary, name="summary"),
    path("", include(router.urls)),
]
