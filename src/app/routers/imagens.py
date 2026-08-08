"""Endpoints das imagens de um paciente (feature imagens-paciente).

Rotas aninhadas no paciente (`/pacientes/{paciente_id}/imagens`), multi-tenant (AD-007).
Uma dependência de router exige que o paciente exista e esteja ativo na clínica do
solicitante → 404 (IMG-07) e isolamento entre clínicas.

Upload em 2 fases (sem órfãos, ver spec):
  POST  → valida tipo + limite de 5, devolve URL pré-assinada de upload (nada gravado).
  (navegador faz PUT do arquivo direto no S3)
  PUT   → confirma que o objeto subiu (head_object) e só então grava o metadado.
O binário nunca passa pela Lambda.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app import s3_images
from app.deps import get_clinic_id
from app.repository import PacienteRepository
from app.repository_imagem import ImagemRepository
from app.schemas_imagem import (
    ImagemConfirm,
    ImagemOut,
    ImagemUploadCreate,
    ImagemUploadOut,
)

LIMITE_IMAGENS = 5


def exigir_paciente(paciente_id: str, clinic_id: str = Depends(get_clinic_id)) -> None:
    """Barra a requisição com 404 se o paciente não existe/está removido na clínica."""
    if PacienteRepository(clinic_id=clinic_id).get(paciente_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente não encontrado")


router = APIRouter(
    prefix="/pacientes/{paciente_id}/imagens",
    tags=["imagens"],
    dependencies=[Depends(exigir_paciente)],
)


def get_repository(
    paciente_id: str, clinic_id: str = Depends(get_clinic_id)
) -> ImagemRepository:
    return ImagemRepository(clinic_id=clinic_id, paciente_id=paciente_id)


@router.get("", response_model=list[ImagemOut])
def listar_imagens(repo: ImagemRepository = Depends(get_repository)) -> list[dict]:
    """Lista as imagens do paciente com URL pré-assinada de download (IMG-03)."""
    return [
        {
            "id": meta["id"],
            "url": s3_images.url_download(meta["key"]),
            "contentType": meta["contentType"],
            "criadoEm": meta["criadoEm"],
        }
        for meta in repo.list()
    ]


@router.post("", response_model=ImagemUploadOut, status_code=status.HTTP_201_CREATED)
def solicitar_upload(
    payload: ImagemUploadCreate,
    paciente_id: str,
    clinic_id: str = Depends(get_clinic_id),
    repo: ImagemRepository = Depends(get_repository),
) -> dict:
    """Valida tipo + limite e devolve a URL pré-assinada de upload (IMG-01, IMG-05, IMG-06)."""
    if not s3_images.content_type_valido(payload.contentType):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagem não aceito. Use JPEG, PNG ou WEBP.",
        )
    if repo.contar() >= LIMITE_IMAGENS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {LIMITE_IMAGENS} imagens por paciente atingido",
        )
    imagem_id = repo.novo_id()
    key = s3_images.montar_key(clinic_id, paciente_id, imagem_id, payload.contentType)
    return {"id": imagem_id, "uploadUrl": s3_images.url_upload(key, payload.contentType)}


@router.put("/{imagem_id}", response_model=ImagemOut)
def confirmar_upload(
    imagem_id: str,
    payload: ImagemConfirm,
    paciente_id: str,
    clinic_id: str = Depends(get_clinic_id),
    repo: ImagemRepository = Depends(get_repository),
) -> dict:
    """Confirma o upload (head_object) e grava o metadado (IMG-02). Idempotente."""
    if not s3_images.content_type_valido(payload.contentType):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagem não aceito. Use JPEG, PNG ou WEBP.",
        )
    existente = repo.get(imagem_id)
    if existente is not None:
        # Confirmação repetida → devolve a imagem já registrada (idempotência).
        return {
            "id": existente["id"],
            "url": s3_images.url_download(existente["key"]),
            "contentType": existente["contentType"],
            "criadoEm": existente["criadoEm"],
        }
    key = s3_images.montar_key(clinic_id, paciente_id, imagem_id, payload.contentType)
    if not s3_images.objeto_existe(key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload não encontrado. Reenvie a imagem.",
        )
    meta = repo.add(imagem_id, key, payload.contentType)
    return {
        "id": meta["id"],
        "url": s3_images.url_download(meta["key"]),
        "contentType": meta["contentType"],
        "criadoEm": meta["criadoEm"],
    }


@router.delete("/{imagem_id}")
def remover_imagem(
    imagem_id: str, repo: ImagemRepository = Depends(get_repository)
) -> dict:
    """Apaga a imagem do S3 e o metadado (IMG-04). `404` se inexistente/de outra clínica."""
    meta = repo.get(imagem_id)
    if meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Imagem não encontrada"
        )
    s3_images.apagar(meta["key"])
    repo.delete(imagem_id)
    return {"detail": "Imagem removida com sucesso"}
