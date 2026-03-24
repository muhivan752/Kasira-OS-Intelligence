from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import uuid
from pydantic import BaseModel, Field

from backend.core.database import get_db
from backend.core.config import settings
from backend.models.outlet import Outlet
from backend.models.product import Product
from backend.models.order import Order, OrderItem
from backend.schemas.response import StandardResponse
import redis.asyncio as redis
from backend.models.connect import ConnectOutlet, ConnectOrder
from backend.models.customer import Customer
import datetime

router = APIRouter()

# Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class ConnectOrderItemInput(BaseModel):
    product_id: uuid.UUID
    qty: int = Field(gt=0)
    notes: Optional[str] = None

class ConnectOrderInput(BaseModel):
    items: List[ConnectOrderItemInput]
    customer_name: str
    customer_phone: str
    order_type: str
    delivery_address: Optional[str] = None
    idempotency_key: str

from backend.services.fonnte import send_whatsapp_message

async def send_wa_confirmation_real(
    phone: str, display_number: str,
    outlet_name: str, customer_name: str
):
    message = (
        f"Pesanan #{display_number} diterima!\n"
        f"Outlet: {outlet_name}\n"
        f"Terima kasih {customer_name}!\n"
        f"Kami segera memproses pesanan Anda."
    )
    await send_whatsapp_message(phone, message)

@router.get("/{slug}", response_model=StandardResponse)
async def get_connect_storefront(slug: str, db: AsyncSession = Depends(get_db)):
    # Check cache
    cache_key = f"connect:storefront:{slug}"
    try:
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return StandardResponse(success=True, data=json.loads(cached_data), message="Storefront retrieved from cache")
    except Exception as e:
        print(f"Redis error: {e}")

    # Get outlet
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    # Get active products with stock > 0
    products_result = await db.execute(
        select(Product).where(
            Product.outlet_id == outlet.id,
            Product.is_active == True,
            Product.stock > 0,
            Product.deleted_at.is_(None)
        )
    )
    products = products_result.scalars().all()

    data = {
        "outlet": {
            "id": str(outlet.id),
            "name": outlet.name,
            "photo": "https://ui-avatars.com/api/?name=" + outlet.name, # Mock photo
            "is_open": outlet.is_open,
            "opening_hours": outlet.opening_hours if outlet.opening_hours else "08:00 - 22:00",
            "trust_badge": "Verified Partner" # Mock trust badge
        },
        "menu": [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "stock": p.stock,
                "image_url": p.image_url
            } for p in products
        ]
    }

    # Set cache
    try:
        await redis_client.setex(cache_key, 60, json.dumps(data))
    except Exception as e:
        print(f"Redis error: {e}")

    return StandardResponse(success=True, data=data, message="Storefront retrieved")

@router.post("/{slug}/order", response_model=StandardResponse)
async def create_connect_order(
    slug: str, 
    input_data: ConnectOrderInput, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    if input_data.order_type not in ["pickup", "delivery"]:
        raise HTTPException(status_code=400, detail="order_type must be pickup or delivery")
    
    if input_data.order_type == "delivery" and not input_data.delivery_address:
        raise HTTPException(status_code=400, detail="delivery_address is required for delivery")

    # Get outlet
    result = await db.execute(
        select(Outlet).where(Outlet.slug == slug, Outlet.deleted_at.is_(None))
    )
    outlet = result.scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    # Check idempotency key
    result = await db.execute(
        select(ConnectOrder).where(ConnectOrder.idempotency_key == input_data.idempotency_key)
    )
    existing_connect_order = result.scalar_one_or_none()
    if existing_connect_order:
        if existing_connect_order.order_id:
            # Get the order
            order_result = await db.execute(
                select(Order).where(Order.id == existing_connect_order.order_id)
            )
            order = order_result.scalar_one_or_none()
            if order:
                return StandardResponse(
                    success=True,
                    data={
                        "order_id": str(order.id),
                        "display_number": order.display_number,
                        "status": order.status,
                        "estimated_minutes": 15 if order.order_type == "pickup" else 30
                    },
                    message="Order retrieved from idempotency key"
                )
        raise HTTPException(status_code=400, detail="Idempotency key already used but order not found")

    # Get or create connect_outlet for storefront
    result = await db.execute(
        select(ConnectOutlet).where(
            ConnectOutlet.outlet_id == outlet.id,
            ConnectOutlet.channel == 'other',
            ConnectOutlet.external_store_id == 'storefront'
        )
    )
    connect_outlet = result.scalar_one_or_none()
    if not connect_outlet:
        connect_outlet = ConnectOutlet(
            outlet_id=outlet.id,
            channel='other',
            external_store_id='storefront'
        )
        db.add(connect_outlet)
        await db.flush()

    # Get or create customer
    result = await db.execute(
        select(Customer).where(
            Customer.tenant_id == outlet.tenant_id,
            Customer.phone == input_data.customer_phone
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        customer = Customer(
            tenant_id=outlet.tenant_id,
            name=input_data.customer_name,
            phone=input_data.customer_phone
        )
        db.add(customer)
        await db.flush()

    # Calculate totals and create order items
    subtotal = 0
    order_items = []
    for item_input in input_data.items:
        result = await db.execute(
            select(Product).where(Product.id == item_input.product_id)
        )
        product = result.scalar_one_or_none()
        if not product or not product.is_active or product.stock < item_input.qty:
            raise HTTPException(status_code=400, detail=f"Product {item_input.product_id} not available or insufficient stock")
        
        # Deduct stock
        product.stock -= item_input.qty
        
        item_total = product.price * item_input.qty
        subtotal += item_total
        
        order_items.append(OrderItem(
            product_id=product.id,
            quantity=item_input.qty,
            unit_price=product.price,
            total_price=item_total,
            notes=item_input.notes
        ))

    # Create order
    today = datetime.datetime.now().strftime("%Y%m%d")
    order_number = f"ORD-{today}-{uuid.uuid4().hex[:6].upper()}"
    
    order = Order(
        outlet_id=outlet.id,
        customer_id=customer.id,
        order_number=order_number,
        status="pending",
        order_type=input_data.order_type,
        subtotal=subtotal,
        total_amount=subtotal, # Simplified, no tax/service charge for now
        notes=f"Delivery Address: {input_data.delivery_address}" if input_data.order_type == "delivery" else None
    )
    db.add(order)
    await db.flush()

    # Add items to order
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    # Create connect order for idempotency
    connect_order = ConnectOrder(
        connect_outlet_id=connect_outlet.id,
        order_id=order.id,
        external_order_id=order_number,
        idempotency_key=input_data.idempotency_key,
        status="pending",
        raw_payload=input_data.model_dump(mode='json')
    )
    db.add(connect_order)
    
    await db.commit()
    await db.refresh(order)

    # Send WA confirmation
    background_tasks.add_task(
        send_wa_confirmation_real,
        input_data.customer_phone,
        str(order.display_number),
        outlet.name,
        input_data.customer_name
    )

    return StandardResponse(
        success=True,
        data={
            "order_id": str(order.id),
            "display_number": order.display_number,
            "status": order.status,
            "estimated_minutes": 15 if order.order_type == "pickup" else 30
        },
        message="Order created successfully"
    )

@router.get("/order/{order_id}", response_model=StandardResponse)
async def get_connect_order_status(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return StandardResponse(
        success=True,
        data={
            "status": order.status,
            "display_number": order.display_number,
            "estimated_minutes": 15 if order.order_type == "pickup" else 30
        },
        message="Order status retrieved"
    )
