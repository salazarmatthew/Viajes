from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.orm import Session
import datetime
import jwt as pyjwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import smtplib
from email.mime.text import MIMEText
import stripe
import logging
import re
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
from dotenv import load_dotenv



# Configuración de la base de datos MySQL
DATABASE_URL = "mysql+pymysql://usuario:password@localhost:3307/reserva_viajes"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Configuración de autenticación
SECRET_KEY = "secret"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración de seguridad y logging
logging.basicConfig(filename="reservas.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def validar_entrada(datos):
    if not re.match(r"^[a-zA-Z0-9_@.-]+$", datos):
        raise HTTPException(status_code=400, detail="Entrada inválida")

# Configuración de correo electrónico
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tu_email@gmail.com"
SMTP_PASSWORD = "tu_contraseña"

STRIPE_SECRET_KEY="sk_test_51QrUQCGfPAhwqfqEW2w9B7CXn8dGLnIvcaVqlB0CovGAvpTnd6xbQ80mkStI58GVMsyPKaSdkwRHQGlWHySDxE5100oxX8XP4o"


# Configuración de Stripe
stripe.api_key = STRIPE_SECRET_KEY


# Cargar el archivo .env
load_dotenv()

# Obtener la clave desde el entorno
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

import requests
from email.mime.text import MIMEText

# Configuración de Mailtrap
MAILTRAP_API_URL = "https://send.api.mailtrap.io/api/v1/inboxes/3456405/messages"
MAILTRAP_API_TOKEN = "200f1fdc3e5f070a5dbe7c27fb60fcea"  # Tu token API Mailtrap

def enviar_correo(destinatario, asunto, mensaje):
    # Estructura del mensaje
    msg = MIMEText(mensaje)
    msg["Subject"] = asunto
    msg["From"] = "tu_email@mailtrap.io"  # Usar el correo desde Mailtrap
    msg["To"] = destinatario
    
    # Datos para enviar el correo mediante la API de Mailtrap
    payload = {
        "to": destinatario,
        "from": "tu_email@mailtrap.io",  # Correo desde Mailtrap
        "subject": asunto,
        "text": mensaje,
        "html": f"<html><body>{mensaje}</body></html>"
    }

    headers = {
        "Authorization": f"Bearer {MAILTRAP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Enviar la solicitud POST a Mailtrap
    response = requests.post(MAILTRAP_API_URL, json=payload, headers=headers)

    # Verificar la respuesta
    if response.status_code == 200:
        print("Correo enviado exitosamente")
    else:
        print(f"Error al enviar el correo. Código de estado: {response.status_code}")
        print(response.text)


# Modelos de la base de datos
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    es_admin = Column(Boolean, default=False)

    # Modelo de datos para registrar un usuario
class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    es_admin: bool = False  # Valor por defecto False

class Viaje(Base):
    __tablename__ = "viajes"
    id = Column(Integer, primary_key=True, index=True)
    destino = Column(String(100), nullable=False)
    fecha_salida = Column(DateTime, nullable=False)
    fecha_regreso = Column(DateTime, nullable=False)
    precio = Column(Float, nullable=False)
    disponibilidad = Column(Integer, nullable=False)

class Reserva(Base):
    __tablename__ = "reservas"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    viaje_id = Column(Integer, ForeignKey("viajes.id"), nullable=False)
    fecha_reserva = Column(DateTime, default=datetime.datetime.utcnow)
    estado = Column(String(20), default="confirmada")
    
    usuario = relationship("Usuario")
    viaje = relationship("Viaje")

# Creación de las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Inicialización de FastAPI
app = FastAPI()

# Dependencia para la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/usuarios")
def registrar_usuario(usuario: UsuarioRegistro, db: Session = Depends(get_db)):
    # Verificar si el usuario ya existe
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    # Hashear la contraseña antes de guardarla
    hashed_password = password_context.hash(usuario.password)

    # Crear nuevo usuario en la base de datos
    nuevo_usuario = Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hashed_password,
        es_admin=usuario.es_admin
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"message": "Usuario creado exitosamente", "usuario_id": nuevo_usuario.id}

# Endpoint de autenticación
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: SessionLocal = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not password_context.verify(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    token = pyjwt.encode({"sub": usuario.email}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

# Endpoint para procesar pagos con Stripe
@app.post("/pago")
def procesar_pago(monto: float, token: str):
    try:
        cargo = stripe.Charge.create(
            amount=int(monto * 100),
            currency="usd",
            source=token,
            description="Pago por reserva de viaje"
        )
        logging.info(f"Pago realizado: {cargo.id}")
        return {"message": "Pago exitoso", "charge_id": cargo.id}
    except stripe.error.StripeError as e:
        logging.error(f"Error en el pago: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error en el pago: {str(e)}")

# Endpoint para reservar un viaje con pago
class ReservaRequest(BaseModel):
    viaje_id: int
    usuario_id: int
    token: str

@app.post("/reservas")
def reservar_viaje_con_pago(reserva_data: ReservaRequest, db: Session = Depends(get_db)):
    viaje = db.query(Viaje).filter(Viaje.id == reserva_data.viaje_id).first()
    usuario = db.query(Usuario).filter(Usuario.id == reserva_data.usuario_id).first()
    
    if not viaje or viaje.disponibilidad <= 0:
        raise HTTPException(status_code=400, detail="Viaje no disponible")

    pago = procesar_pago(viaje.precio, reserva_data.token)

    reserva = Reserva(usuario_id=reserva_data.usuario_id, viaje_id=reserva_data.viaje_id)
    viaje.disponibilidad -= 1
    db.add(reserva)
    db.commit()

    logging.info(f"Reserva confirmada para usuario {reserva_data.usuario_id} en viaje {reserva_data.viaje_id}")
    enviar_correo(usuario.email, "Confirmación de Reserva", f"Su reserva para el viaje a {viaje.destino} ha sido confirmada.")

    return {"message": "Reserva confirmada", "reserva_id": reserva.id, "pago": pago}

# Endpoint para cancelar una reserva
@app.delete("/reservas/{reserva_id}")
def cancelar_reserva(reserva_id: int, db: SessionLocal = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    viaje = db.query(Viaje).filter(Viaje.id == reserva.viaje_id).first()
    viaje.disponibilidad += 1  # Restaurar la disponibilidad del viaje

    db.delete(reserva)
    db.commit()

    usuario = db.query(Usuario).filter(Usuario.id == reserva.usuario_id).first()
    enviar_correo(usuario.email, "Cancelación de Reserva", f"Su reserva para el viaje a {viaje.destino} ha sido cancelada.")

    logging.info(f"Reserva {reserva_id} cancelada para usuario {reserva.usuario_id}")

    return {"message": "Reserva cancelada", "reserva_id": reserva_id}



@app.get("/viajes")
def obtener_viajes(
    destino: Optional[str] = None,
    fecha_inicio: Optional[datetime.date] = None,
    fecha_fin: Optional[datetime.date] = None,
    disponibilidad_minima: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Viaje)

    if destino:
        query = query.filter(Viaje.destino.ilike(f"%{destino}%"))  # Búsqueda parcial
    if fecha_inicio:
        query = query.filter(Viaje.fecha_salida >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Viaje.fecha_regreso <= fecha_fin)
    if disponibilidad_minima:
        query = query.filter(Viaje.disponibilidad >= disponibilidad_minima)

    viajes = query.all()
    return viajes



