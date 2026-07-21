# Cadastro de Pacientes Specification

## Problem Statement

A clínica de Pilates não tem um registro organizado dos seus pacientes. Antes de registrar medidas, pressão, aulas ou consultas, é preciso ter a entidade base — o paciente — cadastrada e gerenciável. Esta feature entrega o CRUD de pacientes, a fundação sobre a qual todas as demais features penduram seus dados (single-table, `PK=CLIENT#<id>`).

## Goals

- [ ] Permitir que a equipe cadastre, consulte, edite e remova (logicamente) pacientes via API.
- [ ] Estabelecer o item de perfil do paciente na tabela DynamoDB (`SK=PROFILE`) conforme a convenção do AD-005.
- [ ] Validar entrada de forma que apenas o Nome seja obrigatório, mantendo cadastro rápido.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Medidas corporais, pressão, aulas, consultas | Features separadas (M2), penduram no mesmo `CLIENT#<id>` |
| Autenticação/login da equipe | Feature separada (M3, Cognito) |
| Interface web (frontend) | Especificada à parte (spec "impecable", M4) |
| Upload de foto/anexos do paciente | Deferido (futuro, S3) |
| Provisionamento da tabela DynamoDB (SAM) | Feature de infraestrutura base (M1) — assume-se a tabela existente |

---

## User Stories

### P1: Cadastrar paciente ⭐ MVP

**User Story**: Como membro da equipe da clínica, quero cadastrar um paciente informando ao menos o nome, para começar a manter sua ficha.

**Why P1**: Sem criar paciente não existe nada sobre o que trabalhar; é a raiz do modelo.

**Acceptance Criteria**:

1. WHEN a equipe envia um cadastro com `nome` preenchido THEN o sistema SHALL criar o paciente, gerar um `id` único e retornar `201` com o paciente criado (incluindo `id` e `criadoEm`).
2. WHEN o cadastro é criado THEN o sistema SHALL persistir o item com `PK=CLIENT#<id>` e `SK=PROFILE`.
3. WHEN o cadastro inclui `dataNascimento`, `endereco`, `telefone` ou `email` THEN o sistema SHALL armazená-los junto ao perfil.
4. WHEN o campo `nome` está ausente ou vazio THEN o sistema SHALL rejeitar com `400` e mensagem indicando que nome é obrigatório.
5. WHEN `email` é informado em formato inválido THEN o sistema SHALL rejeitar com `400`.

**Independent Test**: `POST /pacientes` com `{"nome": "Maria"}` retorna `201` e um `id`; `GET /pacientes/{id}` retorna o mesmo paciente.

---

### P1: Listar pacientes ⭐ MVP

**User Story**: Como membro da equipe, quero listar os pacientes cadastrados, para localizar quem eu quero atender.

**Why P1**: É a forma primária de a equipe encontrar um paciente.

**Acceptance Criteria**:

1. WHEN a equipe solicita a lista THEN o sistema SHALL retornar `200` com os pacientes **ativos** (não removidos logicamente).
2. WHEN não há pacientes THEN o sistema SHALL retornar `200` com lista vazia.
3. WHEN um paciente foi removido logicamente THEN o sistema SHALL omiti-lo da listagem padrão.

**Independent Test**: Após criar 2 pacientes, `GET /pacientes` retorna os 2; após remover 1, retorna 1.

---

### P1: Obter paciente por id ⭐ MVP

**User Story**: Como membro da equipe, quero abrir a ficha de um paciente específico, para ver seus dados.

**Why P1**: Necessário para exibir e editar um paciente.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /pacientes/{id}` de um paciente existente e ativo THEN o sistema SHALL retornar `200` com os dados do paciente.
2. WHEN o `id` não existe THEN o sistema SHALL retornar `404`.
3. WHEN o paciente foi removido logicamente THEN o sistema SHALL retornar `404`.

**Independent Test**: `GET /pacientes/{id}` de um id válido retorna `200`; de um id inexistente retorna `404`.

---

### P1: Editar paciente ⭐ MVP

**User Story**: Como membro da equipe, quero atualizar os dados de um paciente, para manter a ficha correta.

**Why P1**: Dados de contato mudam; correções são inevitáveis.

**Acceptance Criteria**:

1. WHEN a equipe envia `PUT /pacientes/{id}` com dados válidos THEN o sistema SHALL atualizar o perfil e retornar `200` com o paciente atualizado.
2. WHEN a edição deixa `nome` vazio THEN o sistema SHALL rejeitar com `400`.
3. WHEN o `id` não existe ou está removido THEN o sistema SHALL retornar `404`.
4. WHEN o paciente é atualizado THEN o sistema SHALL registrar `atualizadoEm`.

**Independent Test**: `PUT /pacientes/{id}` alterando o telefone retorna `200`; `GET` subsequente reflete a mudança.

---

### P2: Remover paciente (soft delete)

**User Story**: Como membro da equipe, quero remover um paciente que não é mais atendido, sem perder seu histórico clínico.

**Why P2**: Importante para higiene da lista, mas o cadastro é utilizável antes disso; e deve preservar histórico (medidas/aulas futuras).

**Acceptance Criteria**:

1. WHEN a equipe solicita `DELETE /pacientes/{id}` THEN o sistema SHALL marcar o paciente como inativo (soft delete) e retornar `200` com `{"detail": "Paciente removido com sucesso"}`.
2. WHEN um paciente é removido logicamente THEN o sistema SHALL preservar o item no DynamoDB (dado não é apagado fisicamente).
3. WHEN se tenta remover um `id` inexistente ou já removido THEN o sistema SHALL retornar `404`.
4. WHEN um paciente está removido THEN ele SHALL ser omitido da listagem e do `GET` por id padrão.

**Independent Test**: `DELETE /pacientes/{id}` retorna `200` com mensagem de sucesso; `GET /pacientes/{id}` passa a retornar `404`; o item continua na tabela com flag de inativo.

---

## Edge Cases

- WHEN o corpo da requisição não é JSON válido THEN o sistema SHALL retornar `400` com mensagem clara.
- WHEN `nome` contém apenas espaços em branco THEN o sistema SHALL tratar como vazio e rejeitar com `400`.
- WHEN `dataNascimento` é informada em formato inválido (não `YYYY-MM-DD`) THEN o sistema SHALL rejeitar com `400`.
- WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (não persistir lixo).
- WHEN `telefone`/`email` são enviados vazios THEN o sistema SHALL tratar como não informados.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PAC-01 | P1: Cadastrar paciente | T3 | Verified |
| PAC-02 | P1: Cadastrar — persistência PK/SK (AD-005) | T2 | Verified |
| PAC-03 | P1: Cadastrar — validação de nome obrigatório | T1 | Verified |
| PAC-04 | P1: Cadastrar — validação de email | T1 | Verified |
| PAC-05 | P1: Listar pacientes ativos | T2, T4 | Verified |
| PAC-06 | P1: Obter paciente por id | T2, T3 | Verified |
| PAC-07 | P1: Editar paciente | T1, T4 | Verified |
| PAC-08 | P2: Remover paciente (soft delete) | T2, T4 | Verified |
| PAC-09 | Edge cases de validação de entrada | T1 | Verified |

**ID format:** `PAC-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 9 total, 9 mapped to tasks, 0 unmapped ✅ — todos cobertos por teste (45 tests verdes).

---

## Data Model (referência AD-005)

Item de perfil do paciente na tabela única:

```
PK = CLIENT#<id>            (⚠️ mudará para CLINIC#<clinicId>#CLIENT#<id> — ver AD-007/B-003)
SK = PROFILE
Atributos:
  id            (uuid)
  nome          (string, obrigatório)
  cpf           (string, opcional, validado 11 díg + dígitos verificadores, normalizado só números — AD-008)
  dataNascimento(string YYYY-MM-DD, opcional)
  endereco      (MAP opcional, preenchido via CEP no front — AD-009):
                  { cep, logradouro, numero, complemento, bairro, cidade, uf }
  telefone      (string, opcional)
  email         (string, opcional, validado)
  ativo         (bool, default true; false = soft delete)
  criadoEm      (ISO timestamp)
  atualizadoEm  (ISO timestamp)
```

> **Nota (2026-07-21):** `cpf` (AD-008) e `endereco` como MAP (AD-009) foram decididos após o
> deploy inicial. Serão aplicados no refactor do paciente que também introduz o multi-tenant
> (`clinicId` na chave, AD-007/B-003) — os três mexem em `schemas.py`/`repository.py` e serão
> feitos numa única passada antes do M2. A `endereco` deixa de ser string e passa a objeto.

---

## Success Criteria

- [ ] Equipe consegue criar um paciente informando só o nome e recuperá-lo em seguida.
- [ ] Listagem retorna apenas pacientes ativos.
- [ ] Remoção é lógica: paciente some das consultas padrão, mas o item permanece no banco.
- [ ] Todos os 9 requisitos (PAC-01..09) cobertos por teste.
