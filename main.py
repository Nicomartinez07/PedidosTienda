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

class OrderOut(BaseModel):
    id: int
    product: str
    quantity: int

    class Config:
        orm_mode = True

# Rutas de la API

#vizualizar todas las ordenes
@app.get("/orders/", response_model=List[OrderOut], status_code=status.HTTP_200_OK)
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    return orders

#vizualizar una orden en especifico
@app.get("/orders/{order_id}", response_model=OrderOut, status_code=status.HTTP_200_OK)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

# Funciones para insertar y consultar en la base de datos (en caso de necesitarse)
def insert_order(db: Session, product: str, quantity: int) -> Order:
    db_order = Order(product=product, quantity=quantity)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def select_order(db: Session, order_id: int) -> Order:
    return db.query(Order).filter(Order.id == order_id).first()

#HACER UN PEDIDO
@app.post("/orders/", response_model=List[OrderOut], status_code=status.HTTP_201_CREATED)
def create_orders(orders: List[OrderCreate], db: Session = Depends(get_db)):
    db_orders = []
    for order in orders:
        db_order = Order(product=order.product, quantity=order.quantity)
        db.add(db_order)
        db_orders.append(db_order)
    db.commit()  # Confirmar todos los cambios de una vez
    for db_order in db_orders:
        db.refresh(db_order)  # Actualizar cada objeto con su ID generado
    return db_orders



