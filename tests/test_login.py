import pytest
from fastapi.testclient import TestClient
from app import app  # Importa la aplicación FastAPI

# Crear un cliente de prueba para interactuar con la API
client = TestClient(app)


@pytest.fixture()
def crear_usuario():
    # Crear un usuario en la base de datos para las pruebas
    usuario_data = {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "password": "contraseña123",
        "es_admin": False
    }

    # Crear el usuario utilizando el endpoint de registro
    response = client.post("/usuarios", json=usuario_data)
    assert response.status_code == 200
    return usuario_data

def test_login_correcto(crear_usuario):
    # Datos de login correctos
    login_data = {
        "username": "juan@example.com",
        "password": "contraseña123"
    }
    
    # Realizar la solicitud de login
    response = client.post("/token", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"})

    # Verificar que el código de estado sea 200 y que se obtenga un token
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"

def test_login_incorrecto():
    # Datos de login incorrectos
    login_data = {
        "username": "juan@example.com",
        "password": "contraseña_incorrecta"
    }

    # Intentar el login con la contraseña incorrecta
    response = client.post("/token", data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"})

    # Verificar que el código de estado sea 400 para credenciales incorrectas
    assert response.status_code == 400
    assert response.json()["detail"] == "Credenciales incorrectas"
