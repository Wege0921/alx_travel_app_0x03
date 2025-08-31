from django.db import models
import uuid

class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class Booking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    guest_name = models.CharField(max_length=100)
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

from django.conf import settings
from django.db import models
from django.utils import timezone

# If you have an existing Booking model, import it; adjust the path as needed.
# from listings.models import Booking  # example
# For portability here, use a string FK and allow null if not immediately available.

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    # Your booking reference (string) and/or FK to Booking
    booking_ref = models.CharField(max_length=64, db_index=True)
    booking = models.ForeignKey(
        "listings.Booking", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )

    tx_ref = models.CharField(max_length=128, unique=True, help_text="Merchant-defined unique reference")
    chapa_txn_id = models.CharField(max_length=128, blank=True, help_text="Chapa transaction id, if provided")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="ETB")
    customer_email = models.EmailField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    raw_init_response = models.JSONField(null=True, blank=True)
    raw_verify_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_ref} • {self.tx_ref} • {self.status}"

