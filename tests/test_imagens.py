"""Testes dos endpoints de imagens do paciente (IMG-01..07)."""
import boto3
from fastapi.testclient import TestClient

from app import s3_images
from app.main import app

client = TestClient(app)


def _cria_paciente(headers=None):
    return client.post("/pacientes", json={"nome": "Ana"}, headers=headers or {}).json()["id"]


def _sobe_para_s3(bucket, clinic, paciente_id, imagem_id, content_type="image/jpeg"):
    """Simula o upload do navegador ao S3 (o teste não faz o PUT presigned real)."""
    key = s3_images.montar_key(clinic, paciente_id, imagem_id, content_type)
    boto3.client("s3", region_name="us-east-1").put_object(Bucket=bucket, Key=key, Body=b"fake")


def _confirma(bucket, clinic, paciente_id, content_type="image/jpeg", headers=None):
    base = f"/pacientes/{paciente_id}/imagens"
    imagem_id = client.post(base, json={"contentType": content_type}, headers=headers or {}).json()["id"]
    _sobe_para_s3(bucket, clinic, paciente_id, imagem_id, content_type)
    client.put(f"{base}/{imagem_id}", json={"contentType": content_type}, headers=headers or {})
    return imagem_id


def test_fluxo_completo_upload_confirma_lista(imagens_ambiente):
    pid = _cria_paciente()
    base = f"/pacientes/{pid}/imagens"

    # Fase 1: solicita upload → 201 + uploadUrl
    r = client.post(base, json={"contentType": "image/jpeg"})
    assert r.status_code == 201
    img_id = r.json()["id"]
    assert r.json()["uploadUrl"]

    # Antes de confirmar, a imagem não conta nem aparece
    assert client.get(base).json() == []

    # Navegador sobe o arquivo (simulado)
    _sobe_para_s3(imagens_ambiente, "default", pid, img_id)

    # Fase 2: confirma → 200 + url de download
    r2 = client.put(f"{base}/{img_id}", json={"contentType": "image/jpeg"})
    assert r2.status_code == 200
    assert r2.json()["id"] == img_id
    assert r2.json()["url"]
    assert r2.json()["contentType"] == "image/jpeg"

    lst = client.get(base).json()
    assert len(lst) == 1 and lst[0]["id"] == img_id and lst[0]["url"]


def test_confirmar_sem_upload_retorna_400(imagens_ambiente):
    pid = _cria_paciente()
    base = f"/pacientes/{pid}/imagens"
    img_id = client.post(base, json={"contentType": "image/png"}).json()["id"]
    r = client.put(f"{base}/{img_id}", json={"contentType": "image/png"})
    assert r.status_code == 400


def test_confirmar_e_idempotente(imagens_ambiente):
    pid = _cria_paciente()
    base = f"/pacientes/{pid}/imagens"
    img_id = _confirma(imagens_ambiente, "default", pid)
    r = client.put(f"{base}/{img_id}", json={"contentType": "image/jpeg"})
    assert r.status_code == 200
    assert r.json()["id"] == img_id
    assert len(client.get(base).json()) == 1


def test_tipo_invalido_retorna_400(imagens_ambiente):
    pid = _cria_paciente()
    r = client.post(f"/pacientes/{pid}/imagens", json={"contentType": "application/pdf"})
    assert r.status_code == 400


def test_limite_de_5_imagens(imagens_ambiente):
    pid = _cria_paciente()
    base = f"/pacientes/{pid}/imagens"
    for _ in range(5):
        _confirma(imagens_ambiente, "default", pid)
    r = client.post(base, json={"contentType": "image/jpeg"})
    assert r.status_code == 400
    assert "5" in r.json()["detail"]


def test_paciente_inexistente_retorna_404(imagens_ambiente):
    r = client.post("/pacientes/nao-existe/imagens", json={"contentType": "image/jpeg"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Paciente não encontrado"


def test_delete_remove_do_s3_e_libera_vaga(imagens_ambiente):
    pid = _cria_paciente()
    base = f"/pacientes/{pid}/imagens"
    img_id = _confirma(imagens_ambiente, "default", pid)
    r = client.delete(f"{base}/{img_id}")
    assert r.status_code == 200
    assert client.get(base).json() == []
    assert s3_images.objeto_existe(s3_images.montar_key("default", pid, img_id, "image/jpeg")) is False


def test_delete_inexistente_retorna_404(imagens_ambiente):
    pid = _cria_paciente()
    r = client.delete(f"/pacientes/{pid}/imagens/nao-existe")
    assert r.status_code == 404
    assert r.json()["detail"] == "Imagem não encontrada"


def test_isolamento_entre_clinicas(imagens_ambiente):
    a = {"X-Clinic-Id": "clinica-a"}
    b = {"X-Clinic-Id": "clinica-b"}
    pid = _cria_paciente(headers=a)
    _confirma(imagens_ambiente, "clinica-a", pid, headers=a)
    # Clínica B não enxerga o paciente da A → 404 (isolamento)
    assert client.get(f"/pacientes/{pid}/imagens", headers=b).status_code == 404
