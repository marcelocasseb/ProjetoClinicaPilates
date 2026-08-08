# Registro de Sessões (Aula de Pilates) Specification

## Problem Statement

O **core do produto** é registrar, aula a aula, o que cada aluno fez na clínica de Pilates. Hoje o sistema já cadastra pacientes, aparelhos (catálogo por clínica) e avaliações clínicas datadas — mas não há onde lançar a **aula de fato**: quais aparelhos o aluno usou e que tipo de treino fez em cada um. Esta feature entrega o registro de sessões (aulas) por aluno, como histórico datado, consumindo o catálogo de aparelhos já existente e uma taxonomia fixa de tipos de treino.

## Goals

- [x] Permitir registrar uma **aula** de um aluno: data (default hoje) + lista de aparelhos usados, cada um com seus **tipos de treino**.
- [x] Reaproveitar o **catálogo de aparelhos da clínica** (combo box) e guardar um **snapshot (id + nome)** do aparelho na aula — o histórico fica imune a edição/remoção posterior do aparelho no catálogo.
- [x] Oferecer os **tipos de treino** por uma lista fixa (hardcode no front): *Membros superiores, Membros inferiores, Abdômen, Força, Mobilidade, Postural* — armazenados como snapshot de texto (sem enum no back).
- [x] Registrar campos gerais da aula: **observação** (texto livre) e **profissional responsável** (texto livre).
- [x] Consultar as aulas como histórico datado por aluno (mesma UX das avaliações: busca o aluno → lista de datas → abre o detalhe).
- [x] CRUD completo com **soft delete** e fluxo **abrir em leitura → Editar → Salvar**.
- [x] Manter isolamento multi-tenant (AD-007): a clínica A nunca vê nem altera aulas da B.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Detalhe estruturado por aparelho (séries/repetições/carga) | Decisão do usuário: cada aparelho carrega só os **tipos de treino** (texto). Pode virar feature futura |
| Tipos de treino editáveis por clínica (CRUD próprio) | Decisão do usuário: lista **fixa hardcoded** por ora. Vira candidato a CRUD só se o cliente pedir |
| Validação dos tipos de treino contra enum no back | Back guarda o texto como snapshot (padrão flexível do resto do sistema); a lista fixa vive no front |
| Agendamento / calendário de aulas | Esta feature é o **registro** (o que foi feito), não a agenda (o que vai acontecer) |
| Vínculo do profissional a um usuário real | Profissional é **texto livre** por ora — não há usuários/Cognito ainda (M3) |
| Autenticação / login da equipe | Feature separada (M3, Cognito). Por ora `clinicId` vem de `get_clinic_id` (header/default) |

---

## User Stories

### P1: Registrar aula ⭐ MVP

**User Story**: Como membro da equipe, quero registrar a aula de um aluno — a data, os aparelhos que ele usou e o tipo de treino em cada aparelho — para manter o histórico do que foi feito na clínica.

**Why P1**: É o coração do produto; sem isso não há registro de sessões.

**Acceptance Criteria**:

1. WHEN a equipe envia uma aula para um paciente existente da sua clínica com pelo menos um aparelho THEN o sistema SHALL criar a aula, gerar um `id` único e retornar `201` com a aula criada (incluindo `id`, `data` e `criadoEm`).
2. WHEN a aula é criada THEN o sistema SHALL persistir o item com `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>` e `SK=SESSION#<id>`.
3. WHEN a aula inclui aparelhos THEN cada aparelho SHALL ser guardado como snapshot com `aparelhoId` e `nome` (copiados no momento do registro) mais a lista `treinos` (tipos de treino, texto livre).
4. WHEN a aula inclui `observacao` e/ou `profissional` THEN o sistema SHALL armazená-los.
5. WHEN o campo `data` não é enviado THEN o sistema SHALL usar a data de hoje (o front envia a `data` explícita no fuso local, contornando o desvio UTC — ver AD-010).
6. WHEN o `id` do paciente não existe (ou é de outra clínica) THEN o sistema SHALL retornar `404` (aula sempre pende de um aluno válido da própria clínica).

**Independent Test**: `POST /pacientes/{id}/sessoes` com `{"aparelhos":[{"aparelhoId":"a1","nome":"Reformer","treinos":["Força","Mobilidade"]}]}` retorna `201` e um `id`; `GET /pacientes/{id}/sessoes/{sessaoId}` retorna a mesma aula.

---

### P1: Listar aulas do aluno ⭐ MVP

**User Story**: Como membro da equipe, quero buscar um aluno e ver a lista das aulas dele por data, para acompanhar a frequência e a evolução.

**Why P1**: É a forma de consultar o histórico — a tela principal da feature, espelhando a de avaliações.

**Acceptance Criteria**:

1. WHEN a equipe solicita a lista de aulas de um paciente da sua clínica THEN o sistema SHALL retornar `200` com as aulas **ativas** daquele aluno, **ordenadas por data** (mais recente primeiro).
2. WHEN o aluno não tem aulas THEN o sistema SHALL retornar `200` com lista vazia.
3. WHEN uma aula foi removida logicamente THEN o sistema SHALL omiti-la da listagem.
4. WHEN o paciente é de outra clínica ou não existe THEN o sistema SHALL retornar `404`.

**Independent Test**: Criadas 2 aulas para o aluno, `GET /pacientes/{id}/sessoes` retorna 2 itens ordenados por data desc.

---

### P1: Obter aula por id ⭐ MVP

**User Story**: Como membro da equipe, quero abrir uma aula específica, para ver os aparelhos e treinos daquele dia.

**Acceptance Criteria**:

1. WHEN a equipe solicita `GET /pacientes/{id}/sessoes/{sessaoId}` de uma aula existente e ativa do aluno THEN o sistema SHALL retornar `200` com os dados completos (aparelhos, treinos, observação, profissional, data).
2. WHEN o `sessaoId` não existe THEN o sistema SHALL retornar `404`.
3. WHEN a aula foi removida logicamente THEN o sistema SHALL retornar `404`.
4. WHEN o paciente/aula pertence a outra clínica THEN o sistema SHALL retornar `404`.

**Independent Test**: `GET` de uma aula válida da própria clínica retorna `200`; de uma aula de outra clínica retorna `404`.

---

### P1: Aba "Pilates" no front (fluxo da aula) ⭐ MVP

**User Story**: Como membro da equipe, quero uma aba "Pilates" onde eu seleciono o aluno, a data já vem preenchida, adiciono aparelhos por combo box e marco os tipos de treino de cada um, para lançar a aula rapidamente.

**Why P1**: A feature só entrega valor com a tela; o back sozinho não fecha o vertical slice.

**Acceptance Criteria**:

1. WHEN a equipe abre a aba "Pilates" e busca/seleciona um aluno THEN o sistema SHALL iniciar uma aula com a **data de hoje** já preenchida.
2. WHEN a equipe adiciona um aparelho THEN o front SHALL oferecer um **combo box** com os aparelhos **ativos da clínica** (via catálogo existente) e permitir adicionar **vários**.
3. WHEN a equipe escolhe os treinos de um aparelho THEN o front SHALL oferecer a lista fixa (*Membros superiores, Membros inferiores, Abdômen, Força, Mobilidade, Postural*) com seleção múltipla por aparelho.
4. WHEN a equipe salva a aula THEN o front SHALL enviar a `data` explícita (fuso local) e a lista de aparelhos com seus treinos, mais `observacao` e `profissional`.
5. WHEN a equipe consulta um aluno THEN o front SHALL listar as **datas das aulas** (como na tela de avaliações) e, ao clicar numa data, abrir o detalhe **em leitura**; o botão **Editar** destrava a edição e **Salvar** persiste (padrão [[react-button-type-swap-submit]]).
6. WHEN a clínica não tem aparelhos cadastrados THEN o front SHALL orientar a cadastrar aparelhos antes (o combo fica vazio).

**Independent Test**: Na aba Pilates, selecionar um aluno, adicionar "Reformer" com "Força"+"Mobilidade", salvar, e ver a nova data aparecer na lista de aulas do aluno; reabrir mostra os mesmos dados em leitura.

---

### P2: Editar aula

**User Story**: Como membro da equipe, quero corrigir uma aula já lançada (trocar aparelho, ajustar treinos, observação), para manter o histórico correto.

**Why P2**: Higiene do dado; a aula já é utilizável antes disso.

**Acceptance Criteria**:

1. WHEN a equipe envia `PUT /pacientes/{id}/sessoes/{sessaoId}` com dados válidos THEN o sistema SHALL atualizar a aula e retornar `200` com a aula atualizada.
2. WHEN a edição não deixa nenhum aparelho THEN o sistema SHALL rejeitar com `400` (a aula precisa de ao menos um aparelho).
3. WHEN o `sessaoId`/paciente não existe, está removido ou é de outra clínica THEN o sistema SHALL retornar `404`.
4. WHEN a aula é atualizada THEN o sistema SHALL registrar `atualizadoEm`.

**Independent Test**: `PUT` alterando os treinos de um aparelho retorna `200`; `GET` subsequente reflete a mudança.

---

### P2: Remover aula (soft delete)

**User Story**: Como membro da equipe, quero remover uma aula lançada por engano, sem apagar fisicamente o histórico.

**Why P2**: Correção de erro; a aula é utilizável antes disso.

**Acceptance Criteria**:

1. WHEN a equipe solicita `DELETE /pacientes/{id}/sessoes/{sessaoId}` THEN o sistema SHALL marcar a aula como inativa (soft delete) e retornar `200` com `{"detail": "Aula removida com sucesso"}`.
2. WHEN uma aula é removida logicamente THEN o sistema SHALL preservar o item no DynamoDB (não apaga fisicamente).
3. WHEN se tenta remover um `sessaoId` inexistente, já removido, ou de outra clínica THEN o sistema SHALL retornar `404` com `{"detail": "Aula não encontrada"}`.
4. WHEN uma aula está removida THEN ela SHALL ser omitida da listagem e do `GET` por id.

**Independent Test**: `DELETE` retorna `200`; `GET` da aula passa a retornar `404`; o item permanece na tabela com flag de inativo.

---

## Edge Cases

- WHEN o corpo da requisição não é JSON válido THEN o sistema SHALL retornar `400`.
- WHEN a aula é criada sem nenhum aparelho (lista vazia ou ausente) THEN o sistema SHALL rejeitar com `400` (uma aula precisa de ao menos um aparelho).
- WHEN um aparelho da aula vem sem `nome` THEN o sistema SHALL rejeitar com `400` (o snapshot precisa do nome para o histórico).
- WHEN `treinos` de um aparelho vem vazio THEN o sistema SHALL aceitar (aparelho usado sem tipo de treino especificado é válido).
- WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (não persistir lixo).
- WHEN `observacao`/`profissional` são enviados vazios THEN o sistema SHALL tratar como não informados (`None`).
- WHEN o front envia um `aparelhoId` que não existe mais no catálogo THEN o sistema SHALL aceitar mesmo assim (é um snapshot; o back não revalida contra o catálogo — preserva o histórico).

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| SES-01 | P1: Registrar aula | - | Verified |
| SES-02 | P1: Persistência PK/SK sob o paciente (SESSION#<id>) | - | Verified |
| SES-03 | P1: Aparelhos com snapshot (id+nome) + treinos | - | Verified |
| SES-04 | P1: Listar aulas do aluno (datadas, ordenadas) | - | Verified |
| SES-05 | P1: Obter aula por id | - | Verified |
| SES-06 | P1: Validação (paciente inexistente → 404; aula sem aparelho → 400) | - | Verified |
| SES-07 | P2: Editar aula | - | Verified |
| SES-08 | P2: Remover aula (soft delete) | - | Verified |
| SES-09 | Isolamento multi-tenant (não vazar entre clínicas) | - | Verified |
| SES-10 | Edge cases de validação de entrada | - | Verified |
| SES-11 | P1: Front — aba Pilates (seleção aluno, combo aparelhos, treinos, consulta datada, editar/salvar) | - | Verified |

**ID format:** `SES-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 11 total, 0 mapped to tasks, 11 unmapped ⚠️ (mapear na fase de Tasks)

---

## Data Model (referência AD-005 / AD-007 / AD-010)

Item de aula na tabela única, **sob a PK do paciente** (mesma partição do perfil e das avaliações):

```
PK = CLINIC#<clinicId>#CLIENT#<pacienteId>
SK = SESSION#<id>
Atributos:
  id            (uuid)
  data          (string YYYY-MM-DD; default hoje; front envia explícita — fuso local)
  profissional  (string, opcional, texto livre)
  observacao    (string, opcional, texto livre)
  aparelhos     (list<map>, ao menos 1):
    - aparelhoId  (string — snapshot do id do catálogo)
      nome        (string, obrigatório — snapshot do nome no momento do registro)
      treinos     (list<string> — tipos de treino, texto livre; pode ser vazia)
  ativo         (bool, default true; false = soft delete)
  criadoEm      (ISO timestamp)
  atualizadoEm  (ISO timestamp)
```

**Consulta:** `Query` por `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>` + `SK begins_with "SESSION#"`, filtrando `ativo=True`; ordenação por `data` desc **na aplicação** (mesma escolha do AD-010; volume por aluno é baixo). Não colide com `PROFILE` nem `AVALIACAO#...` na mesma PK.

**Snapshot dos aparelhos:** o back **não revalida** os aparelhos contra o catálogo — ele copia `aparelhoId`+`nome` que o front envia. Isso mantém o histórico da aula imune a edição/remoção posterior do aparelho no catálogo (mesma razão do soft delete de aparelho, APR-07).

**Tipos de treino:** lista fixa vive **no front** (hardcode). O back só guarda os textos escolhidos. Sem enum server-side — coerente com o cadastro flexível do resto do sistema.

**Origem do `clinicId`:** `get_clinic_id` (header `X-Clinic-Id`/default hoje; token Cognito no M3).

**Endpoints (aninhados no paciente, como avaliações — AD-010):**

```
POST   /pacientes/{pacienteId}/sessoes        → 201 (cria; 404 se paciente inexistente na clínica)
GET    /pacientes/{pacienteId}/sessoes        → 200 lista (ativas, ordenadas por data desc)
GET    /pacientes/{pacienteId}/sessoes/{id}   → 200 | 404
PUT    /pacientes/{pacienteId}/sessoes/{id}   → 200 | 400 | 404
DELETE /pacientes/{pacienteId}/sessoes/{id}   → 200 | 404 (soft delete)
```

A dependência do router reaproveita `PacienteRepository.get` para garantir 404/isolamento quando o paciente não existe na clínica (mesmo padrão de `routers/avaliacoes.py`).

---

## Success Criteria

- [x] A equipe consegue lançar uma aula selecionando o aluno, adicionando aparelhos por combo box e marcando os tipos de treino, e recuperá-la em seguida.
- [x] A aula guarda snapshot (id+nome) dos aparelhos — editar/remover o aparelho no catálogo depois não altera aulas passadas.
- [x] A consulta por aluno lista as aulas por data (mais recente primeiro) e abre o detalhe em leitura; Editar destrava, Salvar persiste.
- [x] Aulas de outra clínica nunca aparecem nem são acessíveis; paciente inexistente na clínica retorna 404.
- [x] Remoção é lógica: a aula some das consultas, mas o item permanece no banco.
- [x] Todos os requisitos (SES-01..11) cobertos por teste (back) e verificados no front (aba Pilates no ar).
