"""Stripe Webhook / Checkout セッション生成ルータ。"""
from __future__ import annotations

import datetime
import os
import random
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from ..deps import db

router = APIRouter(tags=["stripe"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
_BOT_SECRET = os.getenv("BOT_INTERNAL_SECRET", "")

# Light は割高設定にして Pro へ自然誘導
_EXPAND_UNIT_AMOUNT = {
    "light": 400,
    "pro": 100,
}
_EXPAND_UNIT_ODAI = 100


def _require_bot(x_bot_secret: Optional[str] = Header(None)):
    if not _BOT_SECRET or x_bot_secret != _BOT_SECRET:
        raise HTTPException(status_code=401, detail="Bot認証が必要です")


def _assign_default_odai(guild_id: int, limit: int):
    """Free プラン用: default_odai からランダムに limit 件を guild_default_odai に割り当て。"""
    all_defaults = db.query("SELECT id FROM default_odai WHERE is_active = 1", ())
    if not all_defaults:
        return
    sample = random.sample(all_defaults, min(limit, len(all_defaults)))
    for row in sample:
        db.execute(
            "INSERT IGNORE INTO guild_default_odai (guild_id, default_odai_id) VALUES (%s, %s)",
            (guild_id, row["id"]),
            commit=False,
        )
    db.conn.commit()


def _upsert_guild_plan(guild_id: int, plan: dict, customer_id: str | None, subscription_id: str | None):
    existing = db.query_one("SELECT id FROM guild_plans WHERE guild_id = %s", (guild_id,))
    capacity = plan["custom_odai_base"] or 0
    if existing:
        db.execute(
            "UPDATE guild_plans SET plan_id = %s, custom_odai_capacity = %s, "
            "stripe_customer_id = %s, stripe_subscription_id = %s, status = 'active' "
            "WHERE guild_id = %s",
            (plan["id"], capacity, customer_id, subscription_id, guild_id),
            commit=True,
        )
    else:
        db.execute(
            "INSERT INTO guild_plans "
            "(guild_id, plan_id, custom_odai_capacity, stripe_customer_id, stripe_subscription_id, status) "
            "VALUES (%s, %s, %s, %s, %s, 'active')",
            (guild_id, plan["id"], capacity, customer_id, subscription_id),
            commit=True,
        )


def _handle_checkout_completed(session: dict):
    meta = session.get("metadata", {})
    guild_id = int(meta.get("guild_id", 0))
    if not guild_id:
        return

    session_type = meta.get("type", "subscription")

    if session_type == "expand":
        units = int(meta.get("units", 1))
        db.execute(
            "UPDATE guild_plans SET custom_odai_capacity = custom_odai_capacity + %s WHERE guild_id = %s",
            (units * _EXPAND_UNIT_ODAI, guild_id),
            commit=True,
        )
        return

    plan_name = meta.get("plan", "")
    plan = db.query_one("SELECT * FROM plans WHERE name = %s", (plan_name,))
    if not plan:
        return

    _upsert_guild_plan(
        guild_id, plan,
        customer_id=session.get("customer"),
        subscription_id=session.get("subscription"),
    )

    if plan_name == "free":
        _assign_default_odai(guild_id, plan["default_odai_limit"] or 50)


def _handle_subscription_updated(subscription: dict):
    sub_id = subscription.get("id")
    status = subscription.get("status", "active")
    period_end = subscription.get("current_period_end")
    period_end_dt = (
        datetime.datetime.utcfromtimestamp(period_end).strftime("%Y-%m-%d %H:%M:%S")
        if period_end else None
    )
    db.execute(
        "UPDATE guild_plans SET status = %s, current_period_end = %s WHERE stripe_subscription_id = %s",
        (status, period_end_dt, sub_id),
        commit=True,
    )


def _handle_subscription_deleted(subscription: dict):
    sub_id = subscription.get("id")
    db.execute(
        "UPDATE guild_plans SET status = %s WHERE stripe_subscription_id = %s",
        ("canceled", sub_id),
        commit=True,
    )


@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, _WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="署名検証失敗")
    except Exception:
        raise HTTPException(status_code=400, detail="無効なペイロード")

    etype = event["type"]
    data = event["data"]["object"]

    if etype == "checkout.session.completed":
        _handle_checkout_completed(data)
    elif etype == "customer.subscription.updated":
        _handle_subscription_updated(data)
    elif etype == "customer.subscription.deleted":
        _handle_subscription_deleted(data)

    return {"status": "ok"}


class CheckoutRequest(BaseModel):
    guild_id: int
    plan: str
    success_url: str
    cancel_url: str


@router.post("/api/stripe/checkout", dependencies=[Depends(_require_bot)])
def create_checkout(payload: CheckoutRequest):
    plan = db.query_one("SELECT * FROM plans WHERE name = %s", (payload.plan,))
    if not plan or not plan.get("stripe_price_id"):
        raise HTTPException(status_code=400, detail="有効なプランが見つかりません（stripe_price_id 未設定）")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
        metadata={"guild_id": str(payload.guild_id), "plan": payload.plan, "type": "subscription"},
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return {"url": session.url}


class ExpandRequest(BaseModel):
    guild_id: int
    units: int = 1
    success_url: str
    cancel_url: str


@router.post("/api/stripe/expand", dependencies=[Depends(_require_bot)])
def create_expand_checkout(payload: ExpandRequest):
    gp = db.query_one(
        "SELECT gp.custom_odai_capacity, p.name AS plan_name, "
        "p.can_expand_capacity, p.custom_odai_max "
        "FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id WHERE gp.guild_id = %s",
        (payload.guild_id,),
    )
    if not gp:
        raise HTTPException(status_code=404, detail="プラン情報が見つかりません")
    if not gp["can_expand_capacity"]:
        raise HTTPException(status_code=403, detail="このプランは容量拡張できません")

    plan_name = gp["plan_name"]
    unit_amount = _EXPAND_UNIT_AMOUNT.get(plan_name)
    if unit_amount is None:
        raise HTTPException(status_code=400, detail="拡張価格が未設定です")

    max_cap = gp.get("custom_odai_max")
    if max_cap is not None:
        new_cap = gp["custom_odai_capacity"] + payload.units * _EXPAND_UNIT_ODAI
        if new_cap > max_cap:
            raise HTTPException(status_code=400, detail=f"上限を超えます（最大 {max_cap} 件）")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "jpy",
                "unit_amount": unit_amount,
                "product_data": {"name": f"お題容量拡張 +{_EXPAND_UNIT_ODAI}件 × {payload.units}"},
            },
            "quantity": payload.units,
        }],
        metadata={"guild_id": str(payload.guild_id), "type": "expand", "units": str(payload.units)},
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return {"url": session.url}


@router.get("/api/guilds/{guild_id}/plan")
def get_guild_plan(guild_id: int):
    gp = db.query_one(
        "SELECT gp.custom_odai_capacity, gp.status, gp.current_period_end, "
        "p.name AS plan_name, p.price, p.has_dashboard, p.has_discord_op, "
        "p.can_expand_capacity, p.custom_odai_max "
        "FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id "
        "WHERE gp.guild_id = %s",
        (guild_id,),
    )
    if not gp:
        free = db.query_one(
            "SELECT name AS plan_name, price, has_dashboard, has_discord_op, "
            "can_expand_capacity, custom_odai_max FROM plans WHERE name = 'free'",
            (),
        )
        return {"data": {**(free or {}), "custom_odai_capacity": 0, "status": "active", "current_period_end": None}}
    return {"data": gp}
