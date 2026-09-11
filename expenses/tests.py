from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Budget, Category, Expense, OnboardingProfile, User, UserProfile


class TrackxpensAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            email="owner@example.com",
            password=self.password,
            first_name="Owner",
        )
        UserProfile.objects.create(user=self.user)
        OnboardingProfile.objects.create(user=self.user)
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password=self.password,
        )
        UserProfile.objects.create(user=self.other_user)
        OnboardingProfile.objects.create(user=self.other_user)

    def authenticate(self, user=None):
        user = user or self.user
        self.client.force_authenticate(user=user)

    def create_budget(self, user=None, category_name="Transport"):
        user = user or self.user
        category = Category.objects.create(user=user, name=category_name)
        return Budget.objects.create(
            user=user,
            category=category,
            amount=Decimal("40000.00"),
            account_name="Opay",
        )

    def test_register_creates_user_profile_and_onboarding(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "new@example.com", "password": self.password, "first_name": "New"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertTrue(OnboardingProfile.objects.filter(user=user).exists())
        self.assertNotIn("password", response.data)

    def test_login_accepts_email_and_returns_90_day_tokens(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        token = RefreshToken(response.data["refresh"])
        self.assertGreaterEqual(token.lifetime.days, 90)

    def test_pin_must_be_four_digits_and_can_be_verified(self):
        self.authenticate()

        invalid = self.client.post("/api/pin/set/", {"pin": "123"}, format="json")
        valid = self.client.post("/api/pin/set/", {"pin": "1234"}, format="json")
        wrong = self.client.post("/api/pin/verify/", {"pin": "9999"}, format="json")
        correct = self.client.post("/api/pin/verify/", {"pin": "1234"}, format="json")

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(correct.status_code, 200)
        self.assertTrue(correct.data["unlocked"])

    def test_onboarding_update_marks_profile_complete(self):
        self.authenticate()

        response = self.client.put(
            "/api/onboarding/",
            {
                "has_debt": True,
                "monthly_income": "250000",
                "financial_goal": "Build an emergency fund",
                "money_skills": ["marketing"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["completed_at"])
        self.assertTrue(UserProfile.objects.get(user=self.user).onboarding_complete)

    def test_expense_requires_budget_and_category(self):
        self.authenticate()

        missing_budget = self.client.post(
            "/api/expenses/",
            {"budget_id": 9999, "amount": "2500", "spent_at": str(timezone.localdate())},
            format="json",
        )
        category_response = self.client.post("/api/categories/", {"name": "Feeding"}, format="json")
        budget_response = self.client.post(
            "/api/budgets/",
            {
                "category": category_response.data["id"],
                "amount": "30000",
                "account_name": "UBA",
                "period": "monthly",
            },
            format="json",
        )
        expense_response = self.client.post(
            "/api/expenses/",
            {
                "budget_id": budget_response.data["id"],
                "amount": "2500",
                "note": "Lunch",
                "spent_at": str(timezone.localdate()),
            },
            format="json",
        )

        self.assertEqual(missing_budget.status_code, 400)
        self.assertEqual(category_response.status_code, 201)
        self.assertEqual(budget_response.status_code, 201)
        self.assertEqual(expense_response.status_code, 201)
        self.assertEqual(expense_response.data["category"], "Feeding")

    def test_users_cannot_use_each_others_category_or_budget(self):
        self.authenticate()
        other_category = Category.objects.create(user=self.other_user, name="Private")

        budget_response = self.client.post(
            "/api/budgets/",
            {
                "category": other_category.id,
                "amount": "1000",
                "account_name": "Other bank",
            },
            format="json",
        )
        self.assertEqual(budget_response.status_code, 400)

        other_budget = self.create_budget(user=self.other_user, category_name="Other")
        expense_response = self.client.post(
            "/api/expenses/",
            {"budget_id": other_budget.id, "amount": "100", "spent_at": str(timezone.localdate())},
            format="json",
        )
        self.assertEqual(expense_response.status_code, 400)

    def test_summary_returns_only_current_users_expenses_in_requested_period(self):
        self.authenticate()
        budget = self.create_budget()
        today = timezone.localdate()
        Expense.objects.create(user=self.user, budget=budget, amount=Decimal("2500"), spent_at=today)
        Expense.objects.create(user=self.user, budget=budget, amount=Decimal("1000"), spent_at=today - timedelta(days=2))
        other_budget = self.create_budget(user=self.other_user, category_name="Other")
        Expense.objects.create(user=self.other_user, budget=other_budget, amount=Decimal("9999"), spent_at=today)

        response = self.client.get("/api/summary/?period=month")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(str(response.data["total"])), Decimal("3500"))
        self.assertEqual(len(response.data["by_day"]), 2)
        self.assertEqual(response.data["by_category"][0]["budget__category__name"], "Transport")

    def test_password_reset_request_does_not_reveal_unknown_email(self):
        known = self.client.post("/api/auth/password-reset/", {"email": self.user.email}, format="json")
        unknown = self.client.post("/api/auth/password-reset/", {"email": "missing@example.com"}, format="json")

        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)
