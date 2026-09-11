from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    pin_hash = models.CharField(max_length=128, blank=True)
    require_pin = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default="NGN")
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OnboardingProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="onboarding")
    has_debt = models.BooleanField(default=False)
    monthly_income = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    financial_goal = models.CharField(max_length=120, blank=True)
    money_skills = models.JSONField(default=list, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=80)
    color = models.CharField(max_length=20, default="#1F7A68")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "name"], name="unique_user_category")]
        ordering = ["name"]


class Budget(models.Model):
    PERIODS = [("monthly", "Monthly"), ("yearly", "Yearly")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="budgets")
    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name="budget")
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    account_name = models.CharField(max_length=120)
    period = models.CharField(max_length=20, choices=PERIODS, default="monthly")
    start_date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__name"]


class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="expenses")
    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, related_name="expenses")
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    note = models.CharField(max_length=240, blank=True)
    spent_at = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-spent_at", "-created_at"]


class FinanceLesson(models.Model):
    LEVELS = [("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced")]
    title = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    topic = models.CharField(max_length=80)
    level = models.CharField(max_length=20, choices=LEVELS, default="beginner")
    summary = models.TextField()
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["topic", "title"]
