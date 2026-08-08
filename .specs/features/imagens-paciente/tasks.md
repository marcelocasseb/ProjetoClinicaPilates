# Tasks — Imagens do Paciente

Feature backend-first + front, espelhando o padrão de `avaliacao-pacientes` e `registro-sessoes`
(router aninhado no paciente, dependência que exige paciente ativo → 404/isolamento).
Deploy (SAM/CloudFormation) roda no terminal do usuário — a sessão automatizada não tem SAM/Docker/rede.

## I1 — Infra + helper S3 (IMG-06, IMG-08)
- [x] `template.yaml`: bucket S3 privado `PatientImagesBucket` (BlockPublicAccess total, CORS p/ `PUT`/`GET`/`DELETE` das origens do site + localhost), env `IMAGES_BUCKET` na Lambda, IAM `s3:PutObject/GetObject/DeleteObject` no bucket.
- [x] `src/app/s3_images.py`: tipos aceitos + extensão, `montar_key`, `url_upload` (presigned PUT, SigV4), `url_download` (presigned GET), `objeto_existe` (head_object), `apagar` (delete_object). Cliente boto3 preguiçoso.

## I2 — Schemas + repositório (IMG-01..04, IMG-08)
- [x] `src/app/schemas_imagem.py`: `ImagemUploadCreate` (POST body: contentType), `ImagemUploadOut` (id, uploadUrl), `ImagemConfirm` (PUT body: contentType), `ImagemOut` (id, url, contentType, criadoEm).
- [x] `src/app/repository_imagem.py`: `ImagemRepository(clinic_id, paciente_id)` — `contar`, `add`, `get`, `list` (ordena por criadoEm), `delete` (físico). `SK=IMAGE#<id>`.

## I3 — Router aninhado + fiação (IMG-01..07)
- [x] `src/app/routers/imagens.py`: `GET` (lista + presigned download), `POST` (valida tipo + limite 5 → presigned upload), `PUT /{id}` (confirma via head_object → grava), `DELETE /{id}` (apaga S3 + item). Dependência `exigir_paciente` (404/isolamento).
- [x] `src/app/main.py`: `include_router(imagens.router)`.

## I4 — Testes (IMG-01..08)
- [x] `requirements-dev.txt`: `moto[...,s3]`.
- [x] `tests/test_s3_images.py`: tipo válido/inválido, extensão, presign retorna URL, objeto_existe true/false, apagar.
- [x] `tests/test_repository_imagem.py`: add/get/list/contar/delete + isolamento.
- [x] `tests/test_imagens.py`: fluxo 2 fases (201→upload→confirm 200→GET), limite 5 (400), tipo inválido (400), confirmar sem upload (400), 404 paciente inexistente, isolamento entre clínicas, DELETE + libera vaga.

## I5 — Front (IMG-09)
- [x] `frontend/src/api.js`: `imagensApi` (list/solicitarUpload/confirmar/remove) + helper `uploadParaS3`.
- [x] `frontend/src/components/ImagensPaciente.jsx`: painel com grid de miniaturas, "+ Adicionar" (até 5), remover, validação de tipo/tamanho no front, loading/erro.
- [x] `frontend/src/components/Pacientes.jsx`: renderiza `<ImagensPaciente>` no **fim da ficha** (após Avaliações), só quando o paciente já existe.
- [x] CSS do painel (grid/miniaturas) em `App.css`.

## I6 — Verificação + deploy
- [x] `pytest -q` verde (219); `npm run build` OK; `sam validate --lint` OK.
- [x] `sam deploy` feito (2026-08-07) — bucket criado, changeset aditivo, verificado na stack real. `STATE.md` atualizado.
- [ ] Teste end-to-end no browser com login real (subir/ver/remover imagem).
- [ ] Publicar o front no CloudFront (back no ar; painel ainda não visível ao cliente).
