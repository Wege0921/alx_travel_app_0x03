from django.core.management.base import BaseCommand
from listings.models import Listing
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Seed database with sample listings'

    def handle(self, *args, **kwargs):
        fake = Faker()
        for _ in range(10):
            Listing.objects.create(
                title=fake.company(),
                description=fake.text(),
                location=fake.city(),
                price_per_night=random.uniform(30, 200)
            )
        self.stdout.write(self.style.SUCCESS('Database seeded successfully.'))

