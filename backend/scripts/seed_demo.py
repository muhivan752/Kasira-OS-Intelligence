import asyncio
import os
import sys
from datetime import datetime, timedelta
import random
import uuid

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine
from backend.models import (
    Tenant, Brand, Outlet, User, Role, Category, Product, 
    Order, OrderItem, Payment, Shift
)
from backend.core.security import get_password_hash

async def seed_demo():
    print("Starting demo seed...")
    async with SessionLocal() as db:
        # Create Tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Demo Tenant",
            schema_name="tenant_demo",
            is_active=True
        )
        db.add(tenant)
        await db.commit()
        
        # Create schema for tenant
        async with engine.begin() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {tenant.schema_name}")
            # We would need to run migrations for this schema, but for demo script 
            # we might just use the public schema if schema per tenant is complex,
            # or we need to set search_path.
            
        # Let's just use public schema for demo if it's easier, or set search path
        await db.execute(f"SET search_path TO {tenant.schema_name}, public")
        
        # Actually, since Alembic handles schema creation, we should probably just use the default schema or ensure tables exist.
        # Wait, the models use `__table_args__ = {'schema': 'tenant_name'}` dynamically? No, usually schema is set via search_path.
        
        # Let's create Brand
        brand_id = uuid.uuid4()
        brand = Brand(
            id=brand_id,
            tenant_id=tenant_id,
            name="Kasira Demo Brand"
        )
        db.add(brand)
        
        # Create Outlet
        outlet_id = uuid.uuid4()
        outlet = Outlet(
            id=outlet_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            name="Warung Demo Kasira",
            address="Jl. Demo No. 123, Jakarta",
            phone="081234567890",
            is_active=True
        )
        db.add(outlet)
        
        # Create Role
        role_id = uuid.uuid4()
        role = Role(
            id=role_id,
            tenant_id=tenant_id,
            name="Owner",
            permissions={"all": True}
        )
        db.add(role)
        
        # Create User
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            role_id=role_id,
            full_name="Demo Owner",
            phone="6281234567890",
            pin_hash=get_password_hash("123456"),
            is_active=True
        )
        db.add(user)
        
        await db.commit()
        
        # Create Categories
        categories = [
            Category(id=uuid.uuid4(), tenant_id=tenant_id, brand_id=brand_id, name="Makanan Utama"),
            Category(id=uuid.uuid4(), tenant_id=tenant_id, brand_id=brand_id, name="Minuman"),
            Category(id=uuid.uuid4(), tenant_id=tenant_id, brand_id=brand_id, name="Cemilan"),
            Category(id=uuid.uuid4(), tenant_id=tenant_id, brand_id=brand_id, name="Dessert")
        ]
        db.add_all(categories)
        await db.commit()
        
        # Create 30 Products
        products_data = [
            ("Nasi Goreng Spesial", 25000, categories[0].id),
            ("Mie Goreng Jawa", 22000, categories[0].id),
            ("Ayam Bakar Madu", 30000, categories[0].id),
            ("Sate Ayam Madura", 28000, categories[0].id),
            ("Soto Ayam Lamongan", 20000, categories[0].id),
            ("Nasi Uduk Komplit", 24000, categories[0].id),
            ("Gado-Gado Betawi", 18000, categories[0].id),
            ("Rendang Sapi", 35000, categories[0].id),
            ("Ikan Bakar Rica", 40000, categories[0].id),
            ("Bebek Goreng", 32000, categories[0].id),
            
            ("Es Teh Manis", 5000, categories[1].id),
            ("Es Jeruk Peras", 8000, categories[1].id),
            ("Kopi Susu Gula Aren", 15000, categories[1].id),
            ("Jus Alpukat", 12000, categories[1].id),
            ("Jus Mangga", 12000, categories[1].id),
            ("Lemon Tea", 10000, categories[1].id),
            ("Matcha Latte", 18000, categories[1].id),
            ("Taro Latte", 18000, categories[1].id),
            
            ("Kentang Goreng", 15000, categories[2].id),
            ("Singkong Keju", 12000, categories[2].id),
            ("Pisang Goreng Coklat", 15000, categories[2].id),
            ("Tahu Walik", 12000, categories[2].id),
            ("Tempe Mendoan", 10000, categories[2].id),
            ("Dimsum Ayam", 18000, categories[2].id),
            ("Pangsit Goreng", 15000, categories[2].id),
            
            ("Es Campur", 15000, categories[3].id),
            ("Pudding Coklat", 10000, categories[3].id),
            ("Es Teler", 18000, categories[3].id),
            ("Salad Buah", 20000, categories[3].id),
            ("Brownies Lumer", 25000, categories[3].id),
        ]
        
        products = []
        for name, price, cat_id in products_data:
            p = Product(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                brand_id=brand_id,
                category_id=cat_id,
                name=name,
                base_price=price,
                stock_qty=100,
                is_active=True
            )
            products.append(p)
        
        db.add_all(products)
        await db.commit()
        
        # Create Shift
        now = datetime.utcnow()
        shift_id = uuid.uuid4()
        shift = Shift(
            id=shift_id,
            tenant_id=tenant_id,
            outlet_id=outlet_id,
            user_id=user_id,
            start_time=now - timedelta(days=7),
            end_time=now,
            starting_cash=500000,
            status="closed"
        )
        db.add(shift)
        await db.commit()
        
        # Create 100 Orders over last 7 days
        print("Creating 100 orders...")
        orders = []
        order_items = []
        payments = []
        
        for i in range(100):
            # Random time in last 7 days
            days_ago = random.uniform(0, 7)
            order_time = now - timedelta(days=days_ago)
            
            order_id = uuid.uuid4()
            
            # Random 1-5 items
            num_items = random.randint(1, 5)
            selected_products = random.sample(products, num_items)
            
            total_amount = 0
            for p in selected_products:
                qty = random.randint(1, 3)
                price = p.base_price
                subtotal = qty * price
                total_amount += subtotal
                
                order_items.append(
                    OrderItem(
                        id=uuid.uuid4(),
                        tenant_id=tenant_id,
                        order_id=order_id,
                        product_id=p.id,
                        quantity=qty,
                        unit_price=price,
                        total_price=subtotal
                    )
                )
            
            order = Order(
                id=order_id,
                tenant_id=tenant_id,
                outlet_id=outlet_id,
                shift_session_id=shift_id,
                user_id=user_id,
                order_number=f"ORD-{order_time.strftime('%Y%m%d')}-{i:04d}",
                display_number=i+1,
                status="completed",
                order_type="dine_in",
                subtotal=total_amount,
                total_amount=total_amount,
                created_at=order_time,
                updated_at=order_time
            )
            orders.append(order)
            
            # Payment
            payment_method = random.choice(["cash", "qris"])
            payments.append(
                Payment(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    order_id=order_id,
                    outlet_id=outlet_id,
                    shift_session_id=shift_id,
                    amount_due=total_amount,
                    amount_paid=total_amount,
                    payment_method=payment_method,
                    status="paid",
                    paid_at=order_time,
                    created_at=order_time
                )
            )
            
        db.add_all(orders)
        db.add_all(order_items)
        db.add_all(payments)
        await db.commit()
        
        print("Demo seed completed successfully!")
        print(f"Tenant ID: {tenant_id}")
        print(f"Outlet ID: {outlet_id}")
        print(f"User Phone: 6281234567890")
        print(f"User Password: password123")

if __name__ == "__main__":
    asyncio.run(seed_demo())
