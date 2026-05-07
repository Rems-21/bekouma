"""Client minimal Notch Pay (API REST)."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any
from urllib.parse import quote, urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _public_key() -> str:
    return (getattr(settings, 'NOTCHPAY_PUBLIC_KEY', None) or '').strip()


def _api_base() -> str:
    base = getattr(settings, 'NOTCHPAY_API_BASE', None) or 'https://api.notchpay.co'
    return base.rstrip('/') + '/'


def _headers() -> dict[str, str]:
    key = _public_key()
    if not key:
        return {}
    return {
        'Authorization': key,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def normalize_phone_for_notch(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = ''.join(c for c in phone.strip() if c.isdigit())
    if not digits:
        return None
    if digits.startswith('237'):
        return digits
    if len(digits) == 9 and digits.startswith('6'):
        return '237' + digits
    return digits


def verify_webhook_signature(raw_body: str, signature: str | None, hash_key: str | None) -> bool:
    if not signature or not hash_key:
        return False
    expected = hmac.new(
        hash_key.encode('utf-8'),
        raw_body.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def initialize_checkout(
    *,
    amount: int,
    currency: str,
    reference: str,
    description: str,
    callback_url: str,
    email: str | None,
    phone: str | None,
    customer_name: str | None = None,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    """
    Crée un paiement et renvoie (authorization_url, payload JSON, message d'erreur).
    """
    key = _public_key()
    if not key:
        return None, None, 'NOTCHPAY_PUBLIC_KEY manquant'

    body: dict[str, Any] = {
        'amount': amount,
        'currency': currency,
        'reference': reference,
        'description': description[:500],
        'callback': callback_url,
    }
    em = (email or '').strip()
    ph = normalize_phone_for_notch(phone)
    if em:
        body['email'] = em
    elif ph:
        body['phone'] = ph
    elif customer_name:
        body['customer'] = {'name': customer_name}
    else:
        return None, None, 'Email ou téléphone requis pour Notch Pay'

    url = urljoin(_api_base(), 'payments')
    try:
        r = requests.post(url, json=body, headers=_headers(), timeout=30)
    except requests.RequestException as e:
        logger.exception('Notch Pay initialize network error: %s', e)
        return None, None, str(e)

    try:
        data = r.json()
    except ValueError:
        return None, None, f'Réponse invalide (HTTP {r.status_code})'

    if r.status_code not in (200, 201):
        msg = data.get('message') if isinstance(data, dict) else None
        return None, data if isinstance(data, dict) else None, msg or f'HTTP {r.status_code}'

    auth_url = data.get('authorization_url') if isinstance(data, dict) else None
    if not auth_url:
        return None, data if isinstance(data, dict) else None, 'authorization_url absent'

    return auth_url, data if isinstance(data, dict) else None, None


def retrieve_payment(reference: str) -> dict[str, Any] | None:
    key = _public_key()
    if not key or not reference:
        return None
    url = urljoin(_api_base(), f'payments/{quote(str(reference), safe="")}')
    try:
        r = requests.get(url, headers=_headers(), timeout=20)
    except requests.RequestException as e:
        logger.warning('Notch Pay retrieve error: %s', e)
        return None
    if not (200 <= r.status_code < 300):
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def retrieve_payment_resolved(initial_reference: str, max_hops: int = 6) -> dict[str, Any] | None:
    """
    Suit la chaîne GET /payments/{ref} : référence marchand BEK-…, id interne trx.test_…, ou UUID.
    Ne s'arrête pas sur status « pending » : enchaîne avec transaction.reference si besoin.
    """
    ref: str | None = str(initial_reference).strip() if initial_reference else None
    seen: set[str] = set()
    last_payload: dict[str, Any] | None = None

    for _ in range(max_hops):
        if not ref or ref in seen:
            break
        seen.add(ref)
        payload = retrieve_payment(ref)
        if not payload:
            break
        last_payload = payload
        tx = payload.get('transaction')

        if isinstance(tx, dict):
            if transaction_status_complete(tx):
                return payload
            nxt = tx.get('reference') or tx.get('id') or tx.get('uuid')
            if nxt and str(nxt) not in seen and str(nxt) != ref:
                ref = str(nxt)
                continue
            return payload

        if isinstance(tx, str) and tx.strip():
            nxt = tx.strip()
            if nxt not in seen and nxt != ref:
                ref = nxt
                continue
            break

        break

    return last_payload


def _notch_trx_id_from_initialize(payment) -> str | None:
    init = (getattr(payment, 'gateway_data', None) or {}).get('notchpay_initialize') or {}
    tx = init.get('transaction') if isinstance(init, dict) else None
    if isinstance(tx, dict):
        r = tx.get('reference')
        if r and not str(r).startswith('BEK-'):
            return str(r).strip()
    return None


def retrieve_payment_for_local_order(order, payment) -> dict[str, Any] | None:
    """
    Interroge Notch Pay avec la référence marchand (BEK-…) puis, si besoin, la référence interne
    (trx.test_…) telle que renvoyée à l'initialisation.
    """
    candidates: list[str] = []

    def _add(ref: str | None) -> None:
        if not ref:
            return
        s = str(ref).strip()
        if s and s not in candidates:
            candidates.append(s)

    _add(getattr(order, 'payment_reference', None))
    _add(_notch_trx_id_from_initialize(payment))
    init = (getattr(payment, 'gateway_data', None) or {}).get('notchpay_initialize') or {}
    tx0 = init.get('transaction') if isinstance(init, dict) else None
    if isinstance(tx0, dict):
        for k in ('merchant_reference', 'trxref'):
            _add(tx0.get(k))

    last: dict[str, Any] | None = None
    for start in candidates:
        payload = retrieve_payment_resolved(start, max_hops=6)
        if not payload:
            continue
        last = payload
        tx = extract_transaction(payload)
        if transaction_status_complete(tx):
            return payload
    return last


def transaction_status_complete(transaction: dict[str, Any] | None) -> bool:
    if not transaction or not isinstance(transaction, dict):
        return False
    st = (transaction.get('status') or transaction.get('state') or '').lower()
    if st in (
        'complete',
        'completed',
        'paid',
        'success',
        'successful',
        'succeeded',
        'approved',
    ):
        return True
    if transaction.get('completed_at') or transaction.get('paid_at'):
        return True
    if transaction.get('successful') is True:
        return True
    return False


def extract_transaction(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extrait l’objet « transaction / paiement » des réponses GET /payments/… (formats variables)."""
    if not payload or not isinstance(payload, dict):
        return None
    tx = payload.get('transaction')
    if isinstance(tx, dict) and ('status' in tx or 'reference' in tx or 'id' in tx or 'state' in tx):
        return tx
    if isinstance(tx, str) and tx.strip():
        # Réponse intermédiaire : pas d’objet — la résolution multi-hop est faite ailleurs
        return None
    pay = payload.get('payment')
    if isinstance(pay, dict) and ('status' in pay or 'reference' in pay):
        return pay
    data = payload.get('data')
    if isinstance(data, dict):
        for key in ('transaction', 'payment'):
            inner = data.get(key)
            if isinstance(inner, dict):
                return inner
        if 'reference' in data and ('status' in data or 'state' in data):
            return data
    if 'reference' in payload and ('status' in payload or 'state' in payload):
        return payload
    return None
