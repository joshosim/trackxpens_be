from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Budget, Category, Expense, FinanceLesson, OnboardingProfile, User, UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "first_name"]

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        OnboardingProfile.objects.create(user=user)
        return user


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "color", "is_active"]
        read_only_fields = ["id"]


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Budget
        fields = ["id", "category", "category_name", "amount", "account_name", "period", "start_date", "is_active"]
        read_only_fields = ["id", "category_name"]

    def validate_category(self, category):
        if category.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Choose one of your categories.")
        return category

    def validate(self, attrs):
        if self.instance is None and Budget.objects.filter(category=attrs.get("category")).exists():
            raise serializers.ValidationError({"category": "This category already has a budget."})
        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="budget.category.name", read_only=True)
    budget_id = serializers.PrimaryKeyRelatedField(source="budget", queryset=Budget.objects.all())

    class Meta:
        model = Expense
        fields = ["id", "budget_id", "category", "amount", "note", "spent_at", "created_at"]
        read_only_fields = ["id", "category", "created_at"]

    def validate_budget_id(self, budget):
        if budget.user_id != self.context["request"].user.id or not budget.is_active:
            raise serializers.ValidationError("Choose one of your active budgets.")
        return budget

    def create(self, validated_data):
        return Expense.objects.create(user=self.context["request"].user, **validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False)

    class Meta:
        model = UserProfile
        fields = ["email", "first_name", "currency", "require_pin", "onboarding_complete"]
        read_only_fields = ["email", "onboarding_complete"]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "first_name" in user_data:
            instance.user.first_name = user_data["first_name"]
            instance.user.save(update_fields=["first_name"])
        return super().update(instance, validated_data)


class OnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingProfile
        fields = ["has_debt", "monthly_income", "financial_goal", "money_skills", "completed_at"]
        read_only_fields = ["completed_at"]


class FinanceLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceLesson
        fields = ["id", "title", "slug", "topic", "level", "summary", "content"]
