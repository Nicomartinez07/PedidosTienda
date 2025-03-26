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
    customer_id = Column(Integer, ForeignKey("customers.id"))  # Clave foránea explícita
    quantity = Column(Integer)
    status = Column(String, default="pendiente")
    timestamp = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")  # Relación bidireccional

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)  # Hacemos el nombre único para simplificar
    orders = relationship("Order", back_populates="customer")

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
class CustomerBase(BaseModel):
    name: str

class CustomerCreate(CustomerBase):
    pass

class CustomerOut(CustomerBase):
    id: int
    class Config:
        from_attributes = True


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

@app.post("/orders/", response_model=List[OrderOut], status_code=status.HTTP_201_CREATED)
def create_orders(orders: List[OrderCreate], customer_name: str, db: Session = Depends(get_db)):
    # Verificar si el cliente existe o crearlo
    customer = db.query(Customer).filter(Customer.name == customer_name).first()
    if not customer:
        customer = Customer(name=customer_name)
        db.add(customer)
        db.commit()
        db.refresh(customer)
    
    db_orders = []
    for order in orders:
        if not db.query(Product).filter(Product.id == order.product_id).first():
            raise HTTPException(status_code=400, detail=f"Producto ID {order.product_id} no existe")   
        db_order = Order(
            product_id=order.product_id,
            customer_id=customer.id,
            quantity=order.quantity,
            status=order.status
        )
        db.add(db_order)
        db_orders.append(db_order)
    db.commit()
    for order in db_orders:
        db.refresh(order)
    return db_orders

# Ver el estado de una orden
@app.get("/orders/{order_id}/status/", response_model=OrderOut, status_code=status.HTTP_200_OK)
def get_order_status(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
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


# Crear o obtener un cliente por nombre
@app.post("/customers/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    # Verificar si el cliente ya existe
    existing_customer = db.query(Customer).filter(Customer.name == customer.name).first()
    if existing_customer:
        return existing_customer
    
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

# Obtener historial de pedidos de un cliente por nombre
@app.get("/customers/{customer_name}/orders/", response_model=List[OrderOut], status_code=status.HTTP_200_OK)
def get_customer_orders(customer_name: str, db: Session = Depends(get_db)):
    # Verificar si el cliente existe
    customer = db.query(Customer).filter(Customer.name == customer_name).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Obtener todas las órdenes del cliente
    orders = db.query(Order).filter(Order.customer_id == customer.id).all()
    return orders

