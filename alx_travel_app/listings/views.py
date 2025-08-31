from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer


import uuid
import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Payment
from .serializers import InitiatePaymentSerializer, PaymentSerializer
from .tasks import send_payment_confirmation_email

CHAPA_INIT_URL = f"{settings.CHAPA_BASE_URL}/v1/transaction/initialize"
# Verify docs: GET /v1/transaction/verify/<tx_ref>
CHAPA_VERIFY_URL_TMPL = f"{settings.CHAPA_BASE_URL}/v1/transaction/verify/{{tx_ref}}"

def _auth_headers():
    return {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def initiate_payment(request):
    """
    Create a Payment row (Pending), call Chapa initialize, return checkout URL.
    Request body:
      - booking_ref (str), amount (decimal), email (str)
      - optional: currency (default settings.CHAPA_CURRENCY), first_name, last_name
    Response:
      - payment (serialized), checkout_url (str)
    """
    ser = InitiatePaymentSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    currency = data.get("currency") or getattr(settings, "CHAPA_CURRENCY", "ETB")
    tx_ref = f"bk-{data['booking_ref']}-{uuid.uuid4().hex[:10]}"

    payload = {
        "amount": str(data["amount"]),
        "currency": currency,
        "email": data["email"],
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "tx_ref": tx_ref,
        "callback_url": settings.CHAPA_CALLBACK_URL,  # after payment, you will verify here
        "return_url": settings.CHAPA_RETURN_URL,      # optional user-facing URL
        # (You can add 'customization', 'title', 'description', etc.)
    }

    # Create payment row first (Pending)
    payment = Payment.objects.create(
        booking_ref=data["booking_ref"],
        amount=data["amount"],
        currency=currency,
        customer_email=data["email"],
        tx_ref=tx_ref,
        status=Payment.Status.PENDING,
    )

    try:
        r = requests.post(CHAPA_INIT_URL, json=payload, headers=_auth_headers(), timeout=20)
        resp = r.json()
        payment.raw_init_response = resp
        # Chapa returns a checkout link for redirection in init responses
        checkout_url = resp.get("data", {}).get("checkout_url") or resp.get("data", {}).get("link")
        chapa_txn_id = resp.get("data", {}).get("id") or resp.get("data", {}).get("transaction_id")
        if chapa_txn_id:
            payment.chapa_txn_id = str(chapa_txn_id)
        payment.save(update_fields=["raw_init_response", "chapa_txn_id", "updated_at"])

        if r.status_code >= 400 or not checkout_url:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Failed to initialize payment", "chapa_response": resp},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"payment": PaymentSerializer(payment).data, "checkout_url": checkout_url},
            status=status.HTTP_201_CREATED,
        )

    except requests.RequestException as e:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])
        return Response({"detail": f"Network error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def verify_payment(request):
    """
    Verify a payment using tx_ref (preferred) or ?tx_ref=... from callback.
    Accepts query param: tx_ref
    Updates Payment.status accordingly and triggers confirmation email on success.
    """
    tx_ref = request.query_params.get("tx_ref")
    if not tx_ref:
        return Response({"detail": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.select_for_update().get(tx_ref=tx_ref)
    except Payment.DoesNotExist:
        return Response({"detail": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

    verify_url = CHAPA_VERIFY_URL_TMPL.format(tx_ref=tx_ref)
    try:
        r = requests.get(verify_url, headers=_auth_headers(), timeout=15)
        resp = r.json()
        payment.raw_verify_response = resp

        # Chapa verify returns status for the transaction; treat "success"/"completed" as paid
        # Typical shape: { "status": "success", "data": { "status": "success", ... } }
        top_status = (resp.get("status") or "").lower()
        data_status = (resp.get("data", {}).get("status") or "").lower()
        successful = (top_status in {"success", "completed"}) or (data_status in {"success", "completed"})

        if successful:
            payment.status = Payment.Status.COMPLETED
            payment.save(update_fields=["status", "raw_verify_response", "updated_at"])

            # Fire off email via Celery
            send_payment_confirmation_email.delay(
                payment.customer_email, payment.booking_ref, str(payment.amount), payment.currency
            )
        else:
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status", "raw_verify_response", "updated_at"])

        return Response(PaymentSerializer(payment).data)

    except requests.RequestException as e:
        return Response({"detail": f"Network error: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

from rest_framework import viewsets
from .models import Booking
from .serializers import BookingSerializer
from .tasks import send_booking_confirmation_email

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        # Trigger async email
        send_booking_confirmation_email.delay(
            booking.user.email, booking.id
        )
