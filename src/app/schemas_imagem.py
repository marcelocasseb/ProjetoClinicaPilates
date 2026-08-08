"""Modelos Pydantic das imagens do paciente (feature imagens-paciente).

Fluxo de upload em 2 fases (ver spec):
- `POST` recebe `ImagemUploadCreate` (só o contentType) e devolve `ImagemUploadOut`
  (id + URL pré-assinada de upload). Nada é gravado ainda.
- Depois do upload no S3, `PUT` de confirmação recebe `ImagemConfirm` (o mesmo
  contentType) e devolve `ImagemOut` (metadado + URL de download).
"""
from pydantic import BaseModel, ConfigDict, field_validator


class ImagemUploadCreate(BaseModel):
    """Corpo do `POST /pacientes/{id}/imagens` — solicita a URL de upload."""

    model_config = ConfigDict(extra="ignore")

    contentType: str

    @field_validator("contentType", mode="before")
    @classmethod
    def _limpa(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("contentType é obrigatório")
        return v.strip().lower()


class ImagemConfirm(ImagemUploadCreate):
    """Corpo do `PUT /pacientes/{id}/imagens/{imagemId}` — confirma o upload."""


class ImagemUploadOut(BaseModel):
    """Resposta do `POST` — id da imagem + URL pré-assinada de upload."""

    model_config = ConfigDict(extra="ignore")

    id: str
    uploadUrl: str


class ImagemOut(BaseModel):
    """Representação de saída de uma imagem confirmada (com URL de download)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    url: str
    contentType: str
    criadoEm: str
