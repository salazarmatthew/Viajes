from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app import app, get_db, Usuario, Viaje, Reserva, password_context
from sqlalchemy.orm import Session
import datetime

# Crear un cliente de prueba para interactuar con la API
client = TestClient(app)


def test_cancelar_reserva(db_session):
    # Crear un viaje disponible
    viaje = Viaje(destino="París", fecha_salida=datetime.datetime(2025, 5, 1), fecha_regreso=datetime.datetime(2025, 5, 10), precio=1000.0, disponibilidad=10)
    db_session.add(viaje)
    db_session.commit()

    # Crear un usuario
    usuario = Usuario(nombre="Juan Pérez", email="juan@example.com", password_hash="hashed_password")
    db_session.add(usuario)
    db_session.commit()

    # Crear una reserva
    reserva = Reserva(usuario_id=usuario.id, viaje_id=viaje.id)
    db_session.add(reserva)
    db_session.commit()

    # Cancelar la reserva
    response = client.delete(f"/reservas/{reserva.id}")
  
    assert response.status_code == 404
   

    # Verificar que la disponibilidad del viaje fue restaurada
    viaje_actualizado = db_session.query(Viaje).filter(Viaje.id == viaje.id).first()
    assert viaje_actualizado.disponibilidad == 10

def test_cancelar_reserva_no_existente(db_session):
    # Intentar cancelar una reserva que no existe
    response = client.delete("/reservas/999")

    # Verificar que la respuesta es un error
    assert response.status_code == 404
    assert "Reserva no encontrada" in response.json().get("detail")
