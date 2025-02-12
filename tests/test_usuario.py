from fastapi.testclient import TestClient
from app import app, Usuario

def test_registrar_usuario(db_session, client):
    # Datos del usuario para registrar
    usuario_data = {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "password": "contraseña123",
        "es_admin": False
    }

    # Verificar que el usuario no exista antes de la creación
    usuario_existente = db_session.query(Usuario).filter(Usuario.email == "juan@example.com").first()
    assert usuario_existente is None

    # Registrar el usuario
    response = client.post("/usuarios", json=usuario_data)

    # Verificar que la respuesta es exitosa
    assert response.status_code == 200
    assert "Usuario creado exitosamente" in response.json().get("message")

    # Verificar que el usuario fue realmente creado
    usuario_creado = db_session.query(Usuario).filter(Usuario.email == "juan@example.com").first()
    assert usuario_creado is not None

def test_registrar_usuario_existente(db_session, client):
    # Crear un usuario en la base de datos para probar el caso de usuario existente
    usuario_existente = Usuario(nombre="Juan Pérez", email="juan@example.com", password_hash="hash123")
    db_session.add(usuario_existente)
    db_session.commit()

    # Intentar registrar un usuario con el mismo correo
    usuario_data = {
        "nombre": "Juan Pérez",
        "email": "juan@example.com",
        "password": "contraseña123",
        "es_admin": False
    }
    response = client.post("/usuarios", json=usuario_data)

    # Verificar que la respuesta es un error
    assert response.status_code == 400
    assert "El usuario ya existe" in response.json().get("detail")