from django.core.management.base import BaseCommand

from expenses.models import FinanceLesson


LESSONS = [
    {
        "slug": "build-a-realistic-budget",
        "title": "Build a realistic budget",
        "topic": "Budgeting",
        "level": "beginner",
        "summary": "Give every naira a job before the month starts.",
        "content": "Start with dependable income, list fixed commitments, set category limits, and leave a small buffer for irregular costs. Review actual spending weekly and adjust the next month instead of abandoning the plan.",
    },
    {
        "slug": "escape-the-debt-cycle",
        "title": "Escape the debt cycle",
        "topic": "Debt",
        "level": "beginner",
        "summary": "Turn debt into a visible, ordered plan.",
        "content": "List each balance, interest rate, minimum payment, and due date. Keep minimums current, then direct extra money to either the highest interest rate or the smallest balance, choosing one method and staying consistent.",
    },
    {
        "slug": "sell-a-useful-skill",
        "title": "Sell a useful skill",
        "topic": "Income",
        "level": "beginner",
        "summary": "Find a painful problem and package a clear solution.",
        "content": "Choose one skill you can demonstrate, identify a specific customer, create a small example of your work, and make a simple offer with a clear result, price, and delivery date. Ask for referrals after a successful delivery.",
    },
]


class Command(BaseCommand):
    help = "Seed the starter finance lessons"

    def handle(self, *args, **options):
        for lesson in LESSONS:
            FinanceLesson.objects.update_or_create(slug=lesson["slug"], defaults=lesson)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(LESSONS)} finance lessons."))
