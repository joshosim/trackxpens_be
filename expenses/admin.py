from django.contrib import admin

from .models import Budget, Category, Expense, FinanceLesson, OnboardingProfile, User, UserProfile

admin.site.register([User, UserProfile, OnboardingProfile, Category, Budget, Expense, FinanceLesson])
