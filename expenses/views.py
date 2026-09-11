from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Sum
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Budget, Category, Expense, FinanceLesson, OnboardingProfile, User, UserProfile
from .serializers import (
    BudgetSerializer,
    CategorySerializer,
    ExpenseSerializer,
    FinanceLessonSerializer,
    OnboardingSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related("category")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user).select_related("budget__category")


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class OnboardingView(generics.RetrieveUpdateAPIView):
    serializer_class = OnboardingSerializer

    def get_object(self):
        onboarding, _ = OnboardingProfile.objects.get_or_create(user=self.request.user)
        return onboarding

    def perform_update(self, serializer):
        serializer.save(completed_at=timezone.now())
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        profile.onboarding_complete = True
        profile.save(update_fields=["onboarding_complete", "updated_at"])


class FinanceLessonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinanceLesson.objects.filter(is_published=True)
    serializer_class = FinanceLessonSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
def set_pin(request):
    pin = str(request.data.get("pin", ""))
    if not pin.isdigit() or len(pin) != 4:
        return Response({"detail": "PIN must be exactly 4 digits."}, status=status.HTTP_400_BAD_REQUEST)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    from django.contrib.auth.hashers import make_password
    profile.pin_hash = make_password(pin)
    profile.save(update_fields=["pin_hash", "updated_at"])
    return Response({"detail": "PIN saved.", "require_pin": profile.require_pin})


@api_view(["POST"])
def verify_pin(request):
    from django.contrib.auth.hashers import check_password
    pin = str(request.data.get("pin", ""))
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.pin_hash or not check_password(pin, profile.pin_hash):
        return Response({"detail": "Incorrect PIN."}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"unlocked": True})


@api_view(["POST"])
def reset_pin(request):
    password = request.data.get("password", "")
    pin = str(request.data.get("pin", ""))
    if not authenticate(request, email=request.user.email, password=password):
        return Response({"detail": "Password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    if not pin.isdigit() or len(pin) != 4:
        return Response({"detail": "PIN must be exactly 4 digits."}, status=status.HTTP_400_BAD_REQUEST)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    from django.contrib.auth.hashers import make_password
    profile.pin_hash = make_password(pin)
    profile.save(update_fields=["pin_hash", "updated_at"])
    return Response({"detail": "PIN reset."})


@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
    email = request.data.get("email", "").strip().lower()
    user = User.objects.filter(email=email, is_active=True).first()
    if user:
        token = default_token_generator.make_token(user)
        send_mail(
            "Reset your Trackxpens password",
            f"Use this token with your user id ({user.pk}) to reset your password: {token}",
            None,
            [user.email],
        )
    return Response({"detail": "If that email exists, reset instructions have been sent."})


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    user = User.objects.filter(pk=request.data.get("user_id"), is_active=True).first()
    token = request.data.get("token", "")
    password = request.data.get("password", "")
    if not user or not default_token_generator.check_token(user, token):
        return Response({"detail": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        from django.contrib.auth.password_validation import validate_password
        validate_password(password, user)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password)
    user.save(update_fields=["password"])
    return Response({"detail": "Password reset."})


@api_view(["GET"])
def summary(request):
    period = request.query_params.get("period", "month")
    today = timezone.localdate()
    if period == "day":
        start = end = today
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "year":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
    else:
        start = date(today.year, today.month, 1)
        end = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1) - timedelta(days=1)
    expenses = Expense.objects.filter(user=request.user, spent_at__range=[start, end])
    by_category = list(expenses.values("budget__category__name").annotate(total=Sum("amount")).order_by("budget__category__name"))
    by_day = list(expenses.values("spent_at").annotate(total=Sum("amount")).order_by("spent_at"))
    total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return Response({"period": period, "start": start, "end": end, "total": total, "by_category": by_category, "by_day": by_day})
