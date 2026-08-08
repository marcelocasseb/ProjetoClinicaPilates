# Imagens do Paciente Specification

## Problem Statement

A clínica quer anexar **imagens ao paciente** (fotos posturais, laudos, documentos) direto na ficha, para consulta visual junto do prontuário. Hoje o sistema só guarda texto. Esta feature entrega um **painel de imagens por paciente** (não por consulta) — até **5 imagens** — armazenadas em **Amazon S3** (o binário nunca passa pela Lambda: upload/download por **URL pré-assinada**), com metadados no DynamoDB sob a mesma PK multi-tenant do paciente (AD-005 / AD-007). É a primeira materialização da ideia deferida "upload de fotos/anexos por paciente".

## Goals

- [x] Permitir **adicionar, listar e remover** imagens de um paciente da **própria** clínica, com limite de **5 por paciente**.
- [x] Guardar o **binário no S3** (bucket privado) e apenas os **metadados** no DynamoDB (`SK=IMAGE#<id>` sob a PK do paciente) → a ficha carrega as imagens em 1 Query.
- [x] O binário **não trafega pela Lambda/API Gateway**: o navegador sobe e baixa direto do S3 via **URL pré-assinada** de curta duração (barato, rápido, dentro do free tier).
- [x] Isolamento multi-tenant: a chave do objeto no S3 e o item no Dynamo são escopados por `clinicId`/`pacienteId`; clínica A nunca acessa imagem de B, nem anexa a paciente inexistente na sua clínica.
- [x] "Editar" = remover + adicionar (substituição); reordenar fica fora de escopo.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Imagens **por consulta/avaliação** | Decisão do usuário: as imagens são **por paciente** |
| Edição no próprio browser (crop, rotação, anotação) | Fora do MVP; o usuário sobe a imagem já pronta |
| Miniatura na lista de busca de pacientes | Decisão do usuário: imagens aparecem **só ao abrir a ficha** |
| Geração de thumbnails / redimensionamento server-side | Front limita o tamanho no upload; sem pipeline de imagem por ora |
| Antivírus / verificação de conteúdo do arquivo | Usuários internos e confiáveis; deferido |
| Versionamento / lixeira de imagens | Remoção é física (apaga do S3) — reclama custo de storage |

---

## User Stories

### P1: Adicionar imagem ao paciente ⭐ MVP

**User Story**: Como membro da equipe, quero anexar uma imagem à ficha do paciente, para manter registro visual junto do prontuário.

**Acceptance Criteria**:

1. WHEN a equipe solicita `POST /pacientes/{pacienteId}/imagens` com `{contentType}` de um tipo aceito, para um paciente ativo da sua clínica que ainda tem menos de 5 imagens, THEN o sistema SHALL gerar um `id`, montar a chave S3 isolada e retornar `201` com `{id, uploadUrl}` (URL pré-assinada de `PUT`, expiração curta).
2. WHEN o navegador faz `PUT` do arquivo na `uploadUrl` e em seguida chama `PUT /pacientes/{pacienteId}/imagens/{id}` com `{contentType}` THEN o sistema SHALL confirmar que o objeto existe no S3 (`head_object`), gravar o metadado (`SK=IMAGE#<id>`) e retornar `200` com `{id, url, contentType, criadoEm}` (`url` pré-assinada de download).
3. WHEN o `contentType` não é um tipo de imagem aceito (`image/jpeg`, `image/png`, `image/webp`) THEN o sistema SHALL retornar `400` e NÃO gerar URL de upload.
4. WHEN o paciente já tem 5 imagens THEN o sistema SHALL retornar `400` com `{"detail": "Limite de 5 imagens por paciente atingido"}` e NÃO gerar URL de upload.
5. WHEN a confirmação é chamada mas o objeto não está no S3 (upload falhou/expirou) THEN o sistema SHALL retornar `400` e NÃO gravar o metadado.
6. WHEN o `pacienteId` não existe (ou está removido) na clínica do solicitante THEN o sistema SHALL retornar `404` e NÃO gerar URL nem gravar metadado.

**Independent Test**: `POST` com `{"contentType":"image/jpeg"}` retorna `201` + `uploadUrl`; após `put_object` na chave, `PUT .../imagens/{id}` retorna `200`; `GET` lista a imagem com `url`.

---

### P1: Listar imagens do paciente ⭐ MVP

**User Story**: Como membro da equipe, quero ver as imagens do paciente ao abrir a ficha.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /pacientes/{pacienteId}/imagens` THEN o sistema SHALL retornar `200` com as imagens confirmadas do paciente, cada uma com uma `url` pré-assinada de download (mais antiga primeiro).
2. WHEN o paciente não tem imagens THEN o sistema SHALL retornar `200` com lista vazia.
3. WHEN o `pacienteId` é de outra clínica ou não existe THEN o sistema SHALL retornar `404`.

**Independent Test**: Com 2 imagens confirmadas, `GET` retorna 2 itens com `url`; como outra clínica, `404`.

---

### P1: Remover imagem ⭐ MVP

**User Story**: Como membro da equipe, quero remover uma imagem anexada por engano.

**Acceptance Criteria**:

1. WHEN a equipe solicita `DELETE /pacientes/{pacienteId}/imagens/{id}` de uma imagem existente do paciente THEN o sistema SHALL apagar o objeto do S3, remover o metadado e retornar `200` com `{"detail": "Imagem removida com sucesso"}`.
2. WHEN o `id` não existe, já foi removido, ou é de outra clínica THEN o sistema SHALL retornar `404`.
3. WHEN uma imagem é removida THEN ela SHALL sumir da listagem e liberar uma vaga (volta a permitir até 5).

**Independent Test**: `DELETE` retorna `200`; `GET` subsequente não a inclui; o objeto some do S3.

---

## Edge Cases

- WHEN a confirmação (`PUT`) é chamada para um `id` já confirmado THEN o sistema SHALL ser idempotente e retornar a imagem existente (`200`).
- WHEN o `contentType` da confirmação difere do usado no `POST` THEN a chave reconstruída não casa e o `head_object` falha → `400` (o front reenvia o mesmo tipo).
- WHEN duas solicitações de upload chegam com 4 imagens já confirmadas THEN ambas podem passar (limite verificado sobre imagens **confirmadas**); aceito no volume de uma clínica pequena (uso single-user).
- WHEN o arquivo excede o tamanho máximo THEN o **front** barra antes do upload (checagem de `size`); o back não recebe o binário.

---

## Requirement Traceability

| Requirement ID | Story | Task | Status |
| -------------- | ----- | ---- | ------ |
| IMG-01 | P1: Adicionar — solicitar upload (valida tipo + limite) | I2, I3 | Verified |
| IMG-02 | P1: Adicionar — confirmar (`head_object` + grava metadado) | I2, I3 | Verified |
| IMG-03 | P1: Listar imagens com URL pré-assinada | I2, I3 | Verified |
| IMG-04 | P1: Remover (apaga do S3 + metadado) | I2, I3 | Verified |
| IMG-05 | Limite de 5 imagens por paciente | I3 | Verified |
| IMG-06 | Validação de `contentType` (jpeg/png/webp) | I1, I3 | Verified |
| IMG-07 | 404 se paciente inexistente na clínica + isolamento | I3 | Verified |
| IMG-08 | Chave S3 e item isolados por clínica/paciente | I1, I2 | Verified |
| IMG-09 | Front — painel de imagens na ficha (add/preview/remove, até 5) | I5 | Verified |

**ID format:** `IMG-[NUMBER]`
**Status values:** Pending → Implementing → Verified

---

## Data Model (referência AD-005 / AD-007)

Item de imagem na tabela única, **sob o paciente** (mesma PK do perfil):

```
PK = CLINIC#<clinicId>#CLIENT#<pacienteId>
SK = IMAGE#<id>
Atributos:
  id           (uuid)
  clinicId     (string)
  pacienteId   (string)
  key          (string) — chave do objeto no S3
  contentType  (string) — image/jpeg | image/png | image/webp
  criadoEm     (ISO timestamp)
```

**Binário no S3** (bucket privado `PatientImagesBucket`):
```
Key = <clinicId>/<pacienteId>/<id>.<ext>
```
A `ext` deriva do `contentType` (jpg/png/webp) → a confirmação reconstrói a mesma chave a partir de `id` + `contentType` (não confia numa chave vinda do cliente).

**Fluxo de upload (2 fases, sem órfãos):**
1. `POST` → valida tipo + limite, devolve `uploadUrl` (presigned `PUT`). **Nada é gravado no Dynamo ainda.**
2. Navegador faz `PUT` do arquivo no S3.
3. `PUT` de confirmação → `head_object` garante que subiu; só então grava o metadado. Imagens **não confirmadas nunca contam** e não aparecem.

**Remoção:** física (apaga o objeto no S3 + o item no Dynamo) — imagem é custo de storage, não histórico clínico.

**Isolamento:** o router valida o paciente via `PacienteRepository.get` (dependência) → `404`/isolamento; a chave S3 e o item carregam `clinicId`/`pacienteId` do token, nunca do corpo.

---

## Success Criteria

- [x] A equipe anexa até 5 imagens a um paciente e as vê ao reabrir a ficha.
- [x] O binário sobe/baixa direto do S3 (a Lambda só assina URLs) — dentro do free tier.
- [x] A 6ª imagem é barrada com mensagem clara; remover libera vaga.
- [x] Imagens de outra clínica nunca aparecem nem são acessíveis por id.
- [x] Todos os requisitos IMG-01..09 cobertos por teste (back) + painel verificado no front.
