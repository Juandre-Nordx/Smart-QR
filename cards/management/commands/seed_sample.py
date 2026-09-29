from django.core.management.base import BaseCommand
from cards.models import Company, Person
class Command(BaseCommand):
    help = "Create idempotent fictional development data"
    def handle(self, *args, **options):
        company, _ = Company.objects.update_or_create(name="Example Company", defaults={"website": "https://example.com", "address": "1 Example Street, Cape Town"})
        Person.objects.update_or_create(company=company, email="alex@example.com", defaults={"first_name": "Alex", "last_name": "Example", "position": "Customer Success", "is_active": True})
        self.stdout.write(self.style.SUCCESS("Sample data is ready."))

