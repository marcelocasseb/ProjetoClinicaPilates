# Cadastro de Avaliação dos Pacientes Specification

## Problem Statement

Uma clínica de Pilates avalia fisicamente cada paciente — anamnese, avaliação postural, medidas e inspeção geral — e reavalia ao longo do tratamento para acompanhar a evolução. Hoje o sistema só guarda o **perfil** do paciente; não há onde registrar essas avaliações. Esta feature entrega o CRUD de **avaliações por paciente**, guardadas como **histórico datado** (várias no tempo), sob a mesma PK multi-tenant do paciente (AD-005 / AD-007).

## Goals

- [ ] Permitir registrar, consultar, editar e remover (logicamente) avaliações de um paciente da **própria** clínica.
- [ ] Guardar cada avaliação como item datado (`SK=AVALIACAO#<id>`) sob a PK do paciente (`CLINIC#<clinicId>#CLIENT#<clientId>`) → "evolução do paciente" = 1 Query por PK.
- [ ] Manter cadastro flexível: nenhum campo clínico é obrigatório; a `data` identifica o registro (default hoje).
- [ ] Garantir isolamento multi-tenant: clínica A nunca vê/edita avaliações de B, nem cria avaliação para paciente inexistente na sua clínica.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Tela no front (React) | Esta entrega é **backend primeiro** (decisão do usuário). Front numa etapa seguinte |
| Upload de fotos da avaliação postural / laudos (S3) | Ideia deferida (anexos por paciente) — avaliação postural aqui é texto |
| IMC / antropometria com peso e altura | O usuário definiu **medidas por circunferência** (braço, abdômen, coxa, panturrilha), sem peso/altura → sem campo calculado |
| Escala de dor / força como número estruturado | Ficam dentro de `inspecaoGeral` (texto livre), conforme os campos passados |
| Autenticação / login da equipe | M3 (Cognito). Por ora `clinicId` vem de `get_clinic_id` (header `X-Clinic-Id`/default) |
| Registro de Sessões (aparelhos por sessão) | Feature à parte do M2 (deferida pós-demo) |

---

## User Stories

### P1: Registrar avaliação ⭐ MVP

**User Story**: Como membro da equipe, quero registrar uma avaliação de um paciente da minha clínica, para documentar o estado clínico dele numa data.

**Why P1**: É o núcleo da feature — sem criar não há histórico.

**Acceptance Criteria**:

1. WHEN a equipe envia `POST /pacientes/{pacienteId}/avaliacoes` para um paciente ativo da sua clínica THEN o sistema SHALL criar a avaliação, gerar `id` único e retornar `201` com a avaliação (incluindo `id`, `data`, `criadoEm`).
2. WHEN a criação não informa `data` THEN o sistema SHALL usar a data de hoje (`YYYY-MM-DD`).
3. WHEN a criação informa `data` THEN o sistema SHALL aceitá-la apenas no formato `YYYY-MM-DD` e rejeitar com `400` caso contrário.
4. WHEN a avaliação é criada THEN o sistema SHALL persistir o item com `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>` e `SK=AVALIACAO#<id>`.
5. WHEN o `pacienteId` não existe (ou está removido) na clínica do solicitante THEN o sistema SHALL retornar `404` com `{"detail": "Paciente não encontrado"}` e NÃO criar a avaliação.
6. WHEN a criação inclui quaisquer dos campos clínicos (`diagnosticoMedico`, `queixaPrincipal`, `hma`, `pressaoArterial`, `fc`, `avaliacaoPostural`, `medidas`, `inspecaoGeral`, `examesComplementares`) THEN o sistema SHALL armazená-los; campos ausentes/vazios viram `None`.

**Independent Test**: `POST /pacientes/{id}/avaliacoes` com `{"queixaPrincipal": "dor lombar"}` para um paciente existente retorna `201` com `id` e `data`=hoje; `GET .../avaliacoes/{avId}` retorna a mesma avaliação.

---

### P1: Listar avaliações do paciente ⭐ MVP

**User Story**: Como membro da equipe, quero listar as avaliações de um paciente, para acompanhar a evolução dele ao longo do tempo.

**Why P1**: É como se lê o histórico — o valor principal da feature.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /pacientes/{pacienteId}/avaliacoes` THEN o sistema SHALL retornar `200` com as avaliações **ativas** do paciente, ordenadas por `data` **decrescente** (mais recente primeiro).
2. WHEN o paciente não tem avaliações THEN o sistema SHALL retornar `200` com lista vazia.
3. WHEN uma avaliação foi removida logicamente THEN o sistema SHALL omiti-la da listagem.
4. WHEN o `pacienteId` não existe na clínica do solicitante THEN o sistema SHALL retornar `404`.
5. WHEN existem avaliações de pacientes de outra clínica THEN o sistema SHALL NÃO incluí-las.

**Independent Test**: Criadas 2 avaliações no paciente P, `GET /pacientes/P/avaliacoes` retorna 2, a mais recente primeiro; como outra clínica, retorna `404` para o mesmo `pacienteId`.

---

### P1: Obter avaliação por id ⭐ MVP

**User Story**: Como membro da equipe, quero abrir uma avaliação específica, para ver/editar seus dados.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /pacientes/{pacienteId}/avaliacoes/{avaliacaoId}` de uma avaliação existente e ativa do paciente na sua clínica THEN o sistema SHALL retornar `200` com os dados.
2. WHEN o `avaliacaoId` não existe THEN o sistema SHALL retornar `404` com `{"detail": "Avaliação não encontrada"}`.
3. WHEN a avaliação foi removida logicamente THEN o sistema SHALL retornar `404`.
4. WHEN o `pacienteId` ou o `avaliacaoId` pertence a **outra** clínica THEN o sistema SHALL retornar `404`.

**Independent Test**: `GET .../avaliacoes/{avId}` de um id válido da própria clínica retorna `200`; de um id de outra clínica retorna `404`.

---

### P1: Editar avaliação ⭐ MVP

**User Story**: Como membro da equipe, quero atualizar uma avaliação, para corrigir ou completar o registro.

**Acceptance Criteria**:

1. WHEN a equipe envia `PUT /pacientes/{pacienteId}/avaliacoes/{avaliacaoId}` com dados válidos THEN o sistema SHALL atualizar a avaliação e retornar `200` com a avaliação atualizada.
2. WHEN a edição informa `data` fora do formato `YYYY-MM-DD` THEN o sistema SHALL rejeitar com `400`.
3. WHEN o `avaliacaoId` não existe, está removido, ou o par paciente/avaliação é de outra clínica THEN o sistema SHALL retornar `404`.
4. WHEN a avaliação é atualizada THEN o sistema SHALL registrar `atualizadoEm`.

**Independent Test**: `PUT .../avaliacoes/{avId}` alterando `queixaPrincipal` retorna `200`; `GET` subsequente reflete a mudança.

---

### P2: Remover avaliação (soft delete)

**User Story**: Como membro da equipe, quero remover uma avaliação lançada por engano, sem apagá-la fisicamente do banco.

**Why P2**: Higiene do histórico; o cadastro é utilizável antes disso.

**Acceptance Criteria**:

1. WHEN a equipe solicita `DELETE /pacientes/{pacienteId}/avaliacoes/{avaliacaoId}` THEN o sistema SHALL marcar a avaliação como inativa (soft delete) e retornar `200` com `{"detail": "Avaliação removida com sucesso"}`.
2. WHEN uma avaliação é removida logicamente THEN o sistema SHALL preservar o item no DynamoDB (não apaga fisicamente).
3. WHEN se tenta remover um `avaliacaoId` inexistente, já removido ou de outra clínica THEN o sistema SHALL retornar `404` com `{"detail": "Avaliação não encontrada"}`.
4. WHEN uma avaliação está removida THEN ela SHALL ser omitida da listagem e do `GET` por id.

**Independent Test**: `DELETE .../avaliacoes/{avId}` retorna `200`; `GET` subsequente retorna `404`; o item continua na tabela com flag de inativo.

---

## Edge Cases

- WHEN o corpo da requisição não é JSON válido THEN o sistema SHALL retornar `400`.
- WHEN nenhum campo clínico é informado (só a `data`, ou nem ela) THEN o sistema SHALL aceitar e criar a avaliação (cadastro flexível — a `data` é a identidade).
- WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (`extra="ignore"`).
- WHEN campos de texto (inclusive dentro de `avaliacaoPostural`/`medidas`) são enviados vazios ou só-espaços THEN o sistema SHALL tratá-los como `None`.
- WHEN `avaliacaoPostural`/`medidas` são enviados como objeto sem nenhuma sub-chave preenchida THEN o sistema SHALL armazená-los como `None` (não persistir MAP vazio).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| AVL-01 | P1: Registrar avaliação | A3 | Verified |
| AVL-02 | P1: Registrar — persistência PK/SK sob o paciente | A2 | Verified |
| AVL-03 | P1: Registrar — `data` default hoje + validação `YYYY-MM-DD` | A1 | Verified |
| AVL-04 | P1: Registrar — 404 se paciente inexistente na clínica | A3 | Verified |
| AVL-05 | P1: Listar avaliações ativas ordenadas por data desc | A2, A3 | Verified |
| AVL-06 | P1: Obter avaliação por id | A2, A3 | Verified |
| AVL-07 | P1: Editar avaliação | A1, A2, A3 | Verified |
| AVL-08 | P2: Remover avaliação (soft delete) | A2, A3 | Verified |
| AVL-09 | Isolamento multi-tenant (não vazar entre clínicas) | A2, A3 | Verified |
| AVL-10 | Edge cases de validação/normalização de entrada | A1 | Verified |

**ID format:** `AVL-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 10 total, 10 mapped, 0 unmapped ✅ — implementado em 3 tasks (A1 schemas, A2 repositório, A3 router); 38 testes novos (12 schemas + 14 repositório + 12 endpoints), suíte total 135 verdes.

---

## Data Model (referência AD-005 / AD-007 / AD-009)

Item de avaliação na tabela única, **sob o paciente** (mesma PK do perfil):

```
PK = CLINIC#<clinicId>#CLIENT#<pacienteId>
SK = AVALIACAO#<id>
Atributos:
  id                    (uuid)
  clinicId              (string)
  pacienteId            (string)
  data                  (string YYYY-MM-DD, obrigatório; default = hoje)
  diagnosticoMedico     (string, opcional)
  queixaPrincipal       (string, opcional)
  hma                   (string, opcional — História da Moléstia Atual)
  pressaoArterial       (string, opcional)
  fc                    (string, opcional — frequência cardíaca)
  avaliacaoPostural     (MAP, opcional): { vistaAnterior, vistaLateralDireita,
                                           vistaLateralEsquerda, vistaPosterior }
  medidas               (MAP, opcional): { braco, abdomen, coxa, panturrilha }
  inspecaoGeral         (string, opcional — flexibilidade / grau de força / grau de dor)
  examesComplementares  (string, opcional — exames complementares ou testes)
  ativo                 (bool, default true; false = soft delete)
  criadoEm              (ISO timestamp)
  atualizadoEm          (ISO timestamp)
```

**Chave (SK):** `AVALIACAO#<id>` (id = uuid), **espelhando o padrão de `APARELHO#<id>`** — mantém GET/PUT/DELETE por id triviais (GetItem direto). A `data` fica como atributo e a ordenação por data é feita na aplicação (volume por paciente é baixo). Convive sob a mesma PK do `SK=PROFILE`.

**Listagem:** `Query` na tabela base por `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>` + `SK begins_with "AVALIACAO#"`, filtrando `ativo=True`, ordenada por `data` desc na aplicação. **Não precisa de GSI**.

**Blocos aninhados como MAP:** `avaliacaoPostural` e `medidas` são MAPs (objeto aninhado), no mesmo espírito do `endereco` (AD-009) — casa 1-para-1 com o formulário e mantém o item coeso. MAP sem nenhuma sub-chave preenchida vira `None`.

**Origem do `clinicId`:** `get_clinic_id` (deps.py) — header `X-Clinic-Id`/default hoje; token Cognito no M3.

**Existência do paciente:** o router valida via `PacienteRepository.get(pacienteId)` antes de criar/listar; `None` → `404`. Isso também garante o isolamento (paciente de outra clínica → `None`).

---

## Success Criteria

- [ ] A equipe consegue registrar uma avaliação (mesmo só com a data) e recuperá-la em seguida.
- [ ] A listagem retorna apenas avaliações ativas do paciente, mais recente primeiro.
- [ ] Avaliações/pacientes de outra clínica nunca aparecem nem são acessíveis por id.
- [ ] Criar avaliação para paciente inexistente na clínica retorna `404`.
- [ ] Remoção é lógica: a avaliação some das consultas, mas o item permanece no banco.
- [ ] Todos os 10 requisitos (AVL-01..10) cobertos por teste.
