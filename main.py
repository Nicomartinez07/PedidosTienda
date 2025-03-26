from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from pydantic import BaseModel
from typing import List

# ------------------------- Initial Configuration -------------------------
DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------------  Modelos de tablas DB -------------------------
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    orders = relationship("Order", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    status = Column(String, default="pendiente")
    timestamp = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="orders")

Base.metadata.create_all(bind=engine)


# ------------------------- Agregar Productos -------------------------
def add_sample_products():
    db = SessionLocal()
    try:
        # Check if products already exist
        existing_products = db.query(Product).count()
        if existing_products == 0:
            sample_products = [
                Product(name="Leche"),
                Product(name="Cafe"),
                Product(name="Chocolatada"),
                Product(name="Agua"),
                Product(name="Gaseosa")
            ]
            db.add_all(sample_products)
            db.commit()
            print("Added 5 sample products")
        else:
            print(f"Database already contains {existing_products} products")
    except Exception as e:
        print(f"Error adding sample products: {e}")
    finally:
        db.close()

add_sample_products()

# ------------------------- Pydantic Models -------------------------
class ProductBase(BaseModel):
    name: str

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str

class OrderCreate(BaseModel):
    product_id: int
    quantity: int
    status: str = "pendiente"

class OrderOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    status: str
    timestamp: datetime
    product: ProductOut

    class Config:
        from_attributes = True

# ------------------------- FastAPI Application -------------------------
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Routes

@app.get("/", status_code=status.HTTP_200_OK)
def welcome():
    text = """Bienvenido...           '/orders/' para ver todas las ordenes           '/orders/{num}' para ver orden en especifico"""
    return text

# Get all orders
@app.get("/orders/", response_model=List[OrderOut], status_code=status.HTTP_200_OK)
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return orders

# Get all products - FIXED: Using ProductOut instead of Product
@app.get("/products/", response_model=List[ProductOut], status_code=status.HTTP_200_OK)
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products

# Get specific order
@app.get("/orders/{order_id}", response_model=OrderOut, status_code=status.HTTP_200_OK)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

# Create orders
@app.post("/orders/", response_model=List[OrderOut], status_code=status.HTTP_201_CREATED)
def create_orders(orders: List[OrderCreate], db: Session = Depends(get_db)):
    db_orders = []
    for order in orders:
        if not db.query(Product).filter(Product.id == order.product_id).first():
            raise HTTPException(status_code=400, detail=f"Producto ID {order.product_id} no existe")   
        db_order = Order(
            product_id=order.product_id,
            quantity=order.quantity,
            status=order.status
        )
        db.add(db_order)
        db_orders.append(db_order)
    db.commit()
    # Refresh to get the complete data with relationships
    for order in db_orders:
        db.refresh(order)
    return db_orders

# Ver el estado de una orden
@app.get("/orders/{order_id}/status/", response_model=OrderOut, status_code=status.HTTP_200_OK)
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None: #VERIFICACION SI ORDEN EXISTE
        raise HTTPException(status_code=404, detail="Order not found")
    valid_statuses = ["pendiente", "en proceso", "completado"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid statuses: {valid_statuses}")
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order

# Actualizar el estado de una orden
@app.put("/orders/{order_id}/status/", response_model=OrderOut, status_code=status.HTTP_202_ACCEPTED)
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None: #VERIFICACION SI ORDEN EXISTE
        raise HTTPException(status_code=404, detail="Order not found")
    valid_statuses = ["pendiente", "en proceso", "completado"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid statuses: {valid_statuses}")
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order




