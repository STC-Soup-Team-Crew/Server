# Backend Billing Handoff (for backend agent)

Implement the backend APIs required by the mobile Stripe + Clerk billing flow.

## Required endpoints

### 1) `POST /api/v1/billing/mobile-payment-sheet`
- **Auth:** Clerk Bearer token required.
- **Body:** `{ featureKey?: string, planKey?: string, source?: string }`
- **Behavior:**
  1. Verify Clerk user/session from JWT.
  2. Create or fetch Stripe customer mapped to Clerk user ID.
  3. Create subscription-ready PaymentSheet params.
  4. Return JSON:
     - `paymentIntentClientSecret`
     - `customerId`
     - `customerEphemeralKeySecret`
     - optional `merchantDisplayName`
     - optional `returnUrl`

### 2) `POST /api/v1/billing/customer-portal`
- **Auth:** Clerk Bearer token required.
- **Body:** `{ returnUrl?: string }`
- **Behavior:**
  1. Verify Clerk user/session from JWT.
  2. Resolve Stripe customer.
  3. Create Stripe Billing Portal session.
  4. Return `{ url: string }`.

## Webhooks (required)

Handle these Stripe events:
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`

On relevant events, update Clerk `publicMetadata`:
- `subscriptionStatus` (e.g. `active`, `trialing`, `inactive`, `past_due`)
- `subscriptionPlan` (e.g. `Meal Master Pro`)
- `hasActiveSubscription` (`true`/`false`)
- optional `currentPeriodEnd` (ISO timestamp)

## Operational requirements

- Verify Stripe webhook signature.
- Add idempotency for webhook event processing.
- Log clear error payloads for frontend surfaces.
- Keep Stripe secret keys and webhook secret server-side only.
