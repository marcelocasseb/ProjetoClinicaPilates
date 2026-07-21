# Cadastro de Aparelhos Specification

## Problem Statement

Cada clínica de Pilates tem seu próprio conjunto de aparelhos — e o que existe na clínica A pode não existir na B. Antes de registrar quais aparelhos foram usados numa sessão (feature seguinte do M2), cada clínica precisa manter seu **catálogo de aparelhos**. Esta feature entrega o CRUD de aparelhos, escopado por clínica (multi-tenant, AD-007), que servirá de fonte para o registro de sessões.

## Goals

- [ ] Permitir que a equipe cadastre, consulte, edite e remova (logicamente) os aparelhos da **sua** clínica.
- [ ] Estabelecer o item de aparelho na tabela DynamoDB no nível da clínica (`PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>`).
- [ ] Garantir isolamento: a clínica A nunca vê nem altera aparelhos da B.
- [ ] Manter cadastro rápido: apenas o Nome é obrigatório.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Registro de sessões (uso de aparelhos por paciente) | Feature seguinte do M2 — consome este catálogo |
| Exercícios / procedimentos | Deferido — decidido focar só em aparelhos por ora |
| Quantidade / unidades individuais (ex.: "Reformer 1, 2, 3") | Fora de escopo — catálogo por **tipo** (decisão do usuário: opção A) |
| Categoria como lista fixa / enum | Categoria é **texto livre** (decisão do usuário) |
| Autenticação / login da equipe | Feature separada (M3, Cognito). Por ora `clinicId` vem de `get_clinic_id` (header/default) |
| Manutenção / agenda de aparelhos | Ideia futura |

---

## User Stories

### P1: Cadastrar aparelho ⭐ MVP

**User Story**: Como membro da equipe, quero cadastrar um aparelho da minha clínica informando ao menos o nome, para montar o catálogo que usarei nas sessões.

**Why P1**: Sem catálogo de aparelhos não há o que referenciar nas sessões.

**Acceptance Criteria**:

1. WHEN a equipe envia um cadastro com `nome` preenchido THEN o sistema SHALL criar o aparelho **na clínica do solicitante**, gerar um `id` único e retornar `201` com o aparelho criado (incluindo `id` e `criadoEm`).
2. WHEN o cadastro é criado THEN o sistema SHALL persistir o item com `PK=CLINIC#<clinicId>` e `SK=APARELHO#<id>`.
3. WHEN o cadastro inclui `categoria` ou `descricao` THEN o sistema SHALL armazená-los.
4. WHEN o campo `nome` está ausente ou vazio (ou só espaços) THEN o sistema SHALL rejeitar com `400` e mensagem indicando que nome é obrigatório.

**Independent Test**: `POST /aparelhos` com `{"nome": "Reformer"}` retorna `201` e um `id`; `GET /aparelhos/{id}` retorna o mesmo aparelho.

---

### P1: Listar aparelhos ⭐ MVP

**User Story**: Como membro da equipe, quero listar os aparelhos da minha clínica, para escolher quais foram usados numa sessão.

**Why P1**: É a forma de consultar o catálogo (e alimentará o seletor de aparelhos na sessão).

**Acceptance Criteria**:

1. WHEN a equipe solicita a lista THEN o sistema SHALL retornar `200` com os aparelhos **ativos** da **sua** clínica.
2. WHEN não há aparelhos THEN o sistema SHALL retornar `200` com lista vazia.
3. WHEN um aparelho foi removido logicamente THEN o sistema SHALL omiti-lo da listagem.
4. WHEN existem aparelhos de outra clínica THEN o sistema SHALL NÃO incluí-los na listagem.

**Independent Test**: Criados 2 aparelhos na clínica A e 1 na B, `GET /aparelhos` como A retorna 2; como B retorna 1.

---

### P1: Obter aparelho por id ⭐ MVP

**User Story**: Como membro da equipe, quero abrir um aparelho específico, para ver/editar seus dados.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /aparelhos/{id}` de um aparelho existente e ativo da **sua** clínica THEN o sistema SHALL retornar `200` com os dados.
2. WHEN o `id` não existe THEN o sistema SHALL retornar `404`.
3. WHEN o aparelho foi removido logicamente THEN o sistema SHALL retornar `404`.
4. WHEN o `id` pertence a **outra** clínica THEN o sistema SHALL retornar `404`.

**Independent Test**: `GET /aparelhos/{id}` de um id válido da própria clínica retorna `200`; de um id de outra clínica retorna `404`.

---

### P1: Editar aparelho ⭐ MVP

**User Story**: Como membro da equipe, quero atualizar os dados de um aparelho, para manter o catálogo correto.

**Acceptance Criteria**:

1. WHEN a equipe envia `PUT /aparelhos/{id}` com dados válidos THEN o sistema SHALL atualizar o aparelho e retornar `200` com o aparelho atualizado.
2. WHEN a edição deixa `nome` vazio THEN o sistema SHALL rejeitar com `400`.
3. WHEN o `id` não existe, está removido ou é de outra clínica THEN o sistema SHALL retornar `404`.
4. WHEN o aparelho é atualizado THEN o sistema SHALL registrar `atualizadoEm`.

**Independent Test**: `PUT /aparelhos/{id}` alterando a categoria retorna `200`; `GET` subsequente reflete a mudança.

---

### P2: Remover aparelho (soft delete)

**User Story**: Como membro da equipe, quero remover um aparelho que a clínica não usa mais, sem afetar o histórico de sessões que já o referenciaram.

**Why P2**: Higiene do catálogo; o cadastro é utilizável antes disso. O histórico das sessões é preservado porque a sessão guarda um snapshot (id+nome) do aparelho.

**Acceptance Criteria**:

1. WHEN a equipe solicita `DELETE /aparelhos/{id}` THEN o sistema SHALL marcar o aparelho como inativo (soft delete) e retornar `200` com `{"detail": "Aparelho removido com sucesso"}`.
2. WHEN um aparelho é removido logicamente THEN o sistema SHALL preservar o item no DynamoDB (não apaga fisicamente).
3. WHEN se tenta remover um `id` inexistente, já removido ou de outra clínica THEN o sistema SHALL retornar `404` com `{"detail": "Aparelho não encontrado"}`.
4. WHEN um aparelho está removido THEN ele SHALL ser omitido da listagem e do `GET` por id.

**Independent Test**: `DELETE /aparelhos/{id}` retorna `200`; `GET /aparelhos/{id}` passa a retornar `404`; o item continua na tabela com flag de inativo.

---

## Edge Cases

- WHEN o corpo da requisição não é JSON válido THEN o sistema SHALL retornar `400`.
- WHEN `nome` contém apenas espaços em branco THEN o sistema SHALL tratar como vazio e rejeitar com `400`.
- WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (não persistir lixo).
- WHEN `categoria`/`descricao` são enviados vazios THEN o sistema SHALL tratar como não informados (`None`).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| APR-01 | P1: Cadastrar aparelho | A3 | Verified |
| APR-02 | P1: Cadastrar — persistência PK/SK (nível clínica) | A2 | Verified |
| APR-03 | P1: Cadastrar — validação de nome obrigatório | A1 | Verified |
| APR-04 | P1: Listar aparelhos ativos da clínica | A2, A3 | Verified |
| APR-05 | P1: Obter aparelho por id | A2, A3 | Verified |
| APR-06 | P1: Editar aparelho | A1, A2, A3 | Verified |
| APR-07 | P2: Remover aparelho (soft delete) | A2, A3 | Verified |
| APR-08 | Isolamento multi-tenant (não vazar entre clínicas) | A2, A3 | Verified |
| APR-09 | Edge cases de validação de entrada | A1 | Verified |

**ID format:** `APR-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 9 total, 9 mapped, 0 unmapped ✅ — implementado em 3 tasks (A1 schemas, A2 repositório, A3 endpoints); 96 tests verdes na suíte.

**Implementação (A1–A3):**
- A1 — `src/app/schemas_aparelho.py` + testes (commit schemas)
- A2 — `src/app/repository_aparelho.py` + testes (nível clínica, Query sem GSI, isolamento)
- A3 — `src/app/routers/aparelhos.py` + `src/app/deps.py` (get_clinic_id compartilhado) + fiação no `main.py` + testes de endpoint

---

## Data Model (referência AD-005 / AD-007)

Item de aparelho na tabela única, no **nível da clínica** (não pende do cliente):

```
PK = CLINIC#<clinicId>
SK = APARELHO#<id>
Atributos:
  id            (uuid)
  nome          (string, obrigatório)
  categoria     (string, opcional, texto livre)
  descricao     (string, opcional)
  ativo         (bool, default true; false = soft delete)
  criadoEm      (ISO timestamp)
  atualizadoEm  (ISO timestamp)
```

**Listagem:** `Query` na tabela base por `PK=CLINIC#<clinicId>` + `SK begins_with "APARELHO#"`, filtrando `ativo=True`. **Não precisa de GSI** (todos os aparelhos da clínica compartilham a PK). Não colide com pacientes, cuja PK é mais longa (`CLINIC#<clinicId>#CLIENT#<id>`).

**Origem do `clinicId`:** `get_clinic_id` (reutiliza o mesmo mecanismo do paciente — header `X-Clinic-Id`/default hoje; token Cognito no M3).

---

## Success Criteria

- [ ] A equipe consegue cadastrar um aparelho informando só o nome e recuperá-lo em seguida.
- [ ] A listagem retorna apenas aparelhos ativos da própria clínica.
- [ ] Aparelhos de outra clínica nunca aparecem nem são acessíveis por id.
- [ ] Remoção é lógica: o aparelho some das consultas, mas o item permanece no banco.
- [ ] Todos os 9 requisitos (APR-01..09) cobertos por teste.
