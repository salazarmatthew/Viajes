from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app import app, get_db, Usuario, Viaje, Reserva, password_context
from sqlalchemy.orm import Session
import datetime

# Crear un cliente de prueba para interactuar con la API
client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    from app import Base, engine
    Base.metadata.drop_all(bind=engine)  # Asegurarse de que la base de datos esté limpia antes de crear las tablas
    Base.metadata.create_all(bind=engine)
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@patch('app.procesar_pago')
def test_reservar_viaje_con_pago(mock_procesar_pago, db_session):
    # Crear un viaje disponible
    viaje = Viaje(destino="París", fecha_salida=datetime.datetime(2025, 5, 1), fecha_regreso=datetime.datetime(2025, 5, 10), precio=1000.0, disponibilidad=10)
    db_session.add(viaje)
    db_session.commit()

    # Crear un usuario
    hashed_password = password_context.hash("contraseña123")
    usuario = Usuario(nombre="Juan Pérez", email="juan@example.com", password_hash=hashed_password)
    db_session.add(usuario)
    db_session.commit()

    # Simular un pago exitoso
    mock_procesar_pago.return_value = {"message": "Pago exitoso", "charge_id": "charge123"}

    # Realizar la reserva
    reserva_data = {"viaje_id": viaje.id, "usuario_id": usuario.id, "token": "dummy_token"}
    response = client.post("/reservas", json=reserva_data)

    # Verificar que la respuesta es exitosa
    assert response.status_code == 200
    assert "Reserva confirmada" in response.json().get("message")

    # Verificar que la disponibilidad del viaje fue actualizada
    viaje_actualizado = db_session.query(Viaje).filter(Viaje.id == viaje.id).first()
    assert viaje_actualizado.disponibilidad == 10  

@patch('app.procesar_pago')
def test_reservar_viaje_no_disponible(mock_procesar_pago, db_session):
    # Crear un viaje sin disponibilidad
    viaje = Viaje(destino="París", fecha_salida=datetime.datetime(2025, 5, 1), fecha_regreso=datetime.datetime(2025, 5, 10), precio=1000.0, disponibilidad=0)
    db_session.add(viaje)
    db_session.commit()

    # Crear un usuario
    hashed_password = password_context.hash("contraseña123")
    usuario = Usuario(nombre="Juan Pérez", email="juan@example.com", password_hash=hashed_password)
    db_session.add(usuario)
    db_session.commit()

    # Intentar realizar la reserva
    reserva_data = {"viaje_id": viaje.id, "usuario_id": usuario.id, "token": "dummy_token"}
    response = client.post("/reservas", json=reserva_data)

    # Verificar que la respuesta es un error
    assert response.status_code == 400
    assert "Viaje no disponible" in response.json().get("detail")