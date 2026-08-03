import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_landing_page_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Smile Aesthetic & Dental Clinic" in response.text

def test_chat_api_booking_flow():
    # 1. Mensaje de consulta inicial
    payload1 = {
        "phone_number": "+573112223344",
        "message": "Hola Sofía, me gustaría información sobre Diseño de Sonrisa",
        "channel": "web_chat"
    }
    res1 = client.post("/api/chat", json=payload1)
    assert res1.status_code == 200
    json1 = res1.json()
    assert json1["status"] == "success"
    assert "Smile" in json1["response_text"] or "Diseño" in json1["response_text"]

    # 2. Mensaje de agendamiento
    payload2 = {
        "phone_number": "+573112223344",
        "message": "Quiero agendar cita para diseño de sonrisa para mañana",
        "channel": "web_chat"
    }
    res2 = client.post("/api/chat", json=payload2)
    assert res2.status_code == 200
    json2 = res2.json()
    assert json2["status"] == "success"
    assert len(json2["response_text"]) > 10
