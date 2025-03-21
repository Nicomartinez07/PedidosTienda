from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from pydantic import BaseModel
import jwt
from typing import List

# Configuración de la base de datos
DATABASE_URL = "sqlite:///./orders.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definición de la tabla en SQLAlchemy
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    product = Column(String, index=True)
    quantity = Column(Integer)
    status = Column(String, default="pendiente")  # Estado de la orden
    timestamp = Column(DateTime, default=datetime.utcnow)  # Fecha y hora de creación

# Inicializar la base de datos
Base.metadata.create_all(bind=engine)

# Crear la aplicación FastAPI
app = FastAPI()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelos Pydantic para validar los datos de entrada
class OrderCreate(BaseModel):
    product: str
    quantity: int
    status: str = "pendiente"  # Permite definir el estado al crear una orden

class OrderOut(BaseModel):
    id: int
    product: str
    quantity: int
    status: str
    timestamp: datetime  # Agregar el campo de fecha y hora

    class Config:
        orm_mode = True

class OrderStatusUpdate(BaseModel):
    status: str  # Modelo para actualizar el estado

# Rutas de la API

@app.get("/", status_code=status.HTTP_200_OK)
def welcome():
    text = """Bienvenido...           '/orders/' para ver todas las ordenes           '/orders/{num}' para ver orden en especifico"""
    return text

#vizualizar todas las ordenes
@app.get("/orders/", response_model=List[OrderOut], status_code=status.HTTP_200_OK)
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return orders

#vizualizar una orden en especifico
@app.get("/orders/{order_id}", response_model=OrderOut, status_code=status.HTTP_200_OK)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None: #VERIFICACION SI ORDEN EXISTE
        raise HTTPException(status_code=404, detail="Order not found")
    return order

#HACER UN PEDIDO
@app.post("/orders/", response_model=List[OrderOut], status_code=status.HTTP_201_CREATED)
def create_orders(orders: List[OrderCreate], db: Session = Depends(get_db)):
    db_orders = []
    for order in orders:
        db_order = Order(product=order.product, quantity=order.quantity, status=order.status)
        db.add(db_order)
        db_orders.append(db_order)
    db.commit()  # Confirmar todos los cambios de una vez
    for db_order in db_orders:
        db.refresh(db_order)  # Actualizar cada objeto con su ID generado
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




