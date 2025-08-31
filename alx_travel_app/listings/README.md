# alx_travel_app_0x02 — Chapa Integration

This project integrates Chapa payments for bookings.

## Env
See `.env.example` (not committed). Required:
- CHAPA_SECRET_KEY
- CHAPA_BASE_URL (default https://api.chapa.co)
- CHAPA_CURRENCY (default ETB)
- CHAPA_CALLBACK_URL (e.g., http://localhost:8000/api/payments/verify/)
- CHAPA_RETURN_URL (frontend return page)
- Email settings for confirmation messages

## Models
- listings.Payment
  - booking_ref, tx_ref, chapa_txn_id, amount, currency, customer_email
  - status: PENDING | COMPLETED | FAILED | CANCELED
  - raw_init_response, raw_verify_response

## API
- POST `/api/payments/initiate/`
  - body: { booking_ref, amount, email, [currency], [first_name], [last_name] }
  - returns: { payment, checkout_url }
- GET `/api/payments/verify/?tx_ref=...`
  - verifies with Chapa and updates `Payment.status`

## Flow
1. Create booking.
2. Call `POST /api/payments/initiate/` — get `checkout_url`.
3. User pays on Chapa.
4. Chapa redirects to `CHAPA_CALLBACK_URL` — server calls `verify` to update status.
5. On success, Celery task emails the user.

## Testing
- Use sandbox keys from Chapa dashboard.
- Logs will show `raw_init_response` and `raw_verify_response` saved on `Payment`.
- Attach screenshots of:
  - Successful `initiate` response (checkout URL)
  - Completed sandbox payment page
  - `verify` response showing `COMPLETED`
  - Admin list showing Payment status updated

## Notes
- Endpoints per Chapa docs: initialize & `GET /v1/transaction/verify/<tx_ref>`.
- Consider adding a secured webhook endpoint for resilient confirmations.

