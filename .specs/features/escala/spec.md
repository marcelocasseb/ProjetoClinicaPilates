# Escala Semanal (Grade de Horários) Specification

## Problem Statement

Hoje o sistema registra o que **já aconteceu** (aula lançada na aba Pilates, avaliações datadas),
mas não sabe **quem é esperado quando**. A clínica organiza os alunos em uma **grade fixa da
semana** ("Rebecca vem segunda e quarta às 7h") que hoje vive num papel ou na cabeça da recepção.
Esta feature entrega uma aba **Escala**: uma tabela de **7 colunas** (segunda a domingo) onde as
**linhas são os horários** e cada célula mostra os alunos matriculados naquele dia/hora.

## Goals

- [ ] Ver, numa tela só, a **grade da semana inteira** da clínica: 7 dias × horários, com os alunos de cada faixa.
- [ ] **Matricular** um aluno num dia+horário e **removê-lo** dali, direto na grade.
- [ ] Mostrar a **contagem de alunos** por horário (a recepção enxerga lotação sem precisar contar).
- [ ] Manter isolamento multi-tenant (AD-007): a clínica A nunca vê nem altera a escala da B.
- [ ] **Sem mudança de infraestrutura**: reaproveitar a partição de nível clínica já existente
      (`PK=CLINIC#<clinicId>`, onde já moram `METADATA` e `APARELHO#<id>`) — sem tabela nova, sem GSI novo.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Exceções por data (falta, reposição, feriado, "semana que vem não venho") | Decisão do usuário: v1 é **grade fixa recorrente**. O prefixo de SK deixa espaço para um `AGENDA#<data>#…` depois |
| Capacidade / limite de alunos por horário | Decisão do usuário: **sem limite**, a célula só mostra a contagem. O limite real (nº de aparelhos) fica com o julgamento da recepção |
| Profissional responsável por horário | Decisão do usuário: a grade guarda **só os alunos**. O profissional já é registrado na aula (aba Pilates), onde importa para o histórico clínico |
| Horários configuráveis por clínica (item `CONFIG#ESCALA`) | Decisão do usuário: lista **fixa hardcoded no front**, como os tipos de treino (AD-011). Vira candidato a config se um cliente pedir outro horário de funcionamento |
| Marcar presença / gerar a aula a partir da escala | Fase 2 — a integração "hoje às 08:00 tem X, Y, Z → iniciar aula" depende desta grade existir primeiro |
| Notificação/lembrete ao aluno | Não há canal com o aluno (o sistema é interno da clínica) |

---

## User Stories

### P1: Ver a grade da semana ⭐ MVP

**User Story**: Como recepção da clínica, quero abrir uma aba "Escala" e ver a semana inteira —
segunda a domingo nas colunas, horários nas linhas — com os alunos de cada faixa, para saber quem
é esperado quando.

**Why P1**: É a tela da feature; sem ela não há valor nenhum.

**Acceptance Criteria**:

1. WHEN a equipe solicita a escala da sua clínica THEN o sistema SHALL retornar `200` com todas as matrículas, cada uma com `dia`, `hora`, `pacienteId` e `nome`.
2. WHEN a escala é montada THEN o sistema SHALL devolver as matrículas **ordenadas por dia → hora → nome** (a ordem de renderização da grade).
3. WHEN a clínica não tem nenhuma matrícula THEN o sistema SHALL retornar `200` com lista vazia (a grade aparece vazia, não quebra).
4. WHEN o front renderiza a grade THEN ele SHALL exibir **7 colunas** (segunda…domingo) e, nas linhas, a **lista fixa de horários** somada a qualquer horário que já tenha matrícula (nenhum aluno fica invisível por estar fora da lista fixa).
5. WHEN uma célula tem alunos THEN o front SHALL exibir o nome de cada um e a **contagem** do horário.

**Independent Test**: `GET /escala` com 3 matrículas retorna as 3 ordenadas por dia/hora; a aba Escala mostra os nomes nas células certas.

---

### P1: Matricular aluno num horário ⭐ MVP

**User Story**: Como recepção, quero adicionar um aluno a um dia+horário da grade, para registrar o horário fixo dele.

**Why P1**: Sem escrita a grade nasce vazia e permanente vazia.

**Acceptance Criteria**:

1. WHEN a equipe envia `POST /escala` com `dia`, `hora` e `pacienteId` de um aluno ativo da sua clínica THEN o sistema SHALL criar a matrícula e retornar `201` com `dia`, `hora`, `pacienteId` e `nome`.
2. WHEN a matrícula é criada THEN o sistema SHALL persistir o item com `PK=CLINIC#<clinicId>` e `SK=ESCALA#<dia>#<hora>#<pacienteId>`.
3. WHEN o aluno **já está** naquele mesmo dia+horário THEN o sistema SHALL retornar `409` (sem duplicar a linha na célula).
4. WHEN o `pacienteId` não existe, está removido, ou é de outra clínica THEN o sistema SHALL retornar `404`.
5. WHEN a matrícula é criada THEN o sistema SHALL gravar `pacienteNome` como snapshot e `criadoEm`.

**Independent Test**: `POST /escala {"dia":1,"hora":"07:00","pacienteId":"<id>"}` retorna `201`; repetir a mesma chamada retorna `409`; `GET /escala` mostra uma única matrícula.

---

### P1: Remover aluno de um horário ⭐ MVP

**User Story**: Como recepção, quero tirar um aluno de um horário quando ele muda de dia ou sai da clínica, para a grade refletir a realidade.

**Acceptance Criteria**:

1. WHEN a equipe envia `DELETE /escala/{dia}/{hora}/{pacienteId}` de uma matrícula existente THEN o sistema SHALL removê-la e retornar `200` com `{"detail": "Aluno removido do horário"}`.
2. WHEN a matrícula não existe (ou é de outra clínica) THEN o sistema SHALL retornar `404` com `{"detail": "Matrícula não encontrada"}`.
3. WHEN uma matrícula é removida THEN o sistema SHALL apagá-la **fisicamente** do DynamoDB (ver "Remoção física" no Data Model — desvio consciente do soft delete do resto do sistema).
4. WHEN a matrícula é removida THEN ela SHALL sumir da grade imediatamente.

**Independent Test**: `DELETE` de uma matrícula existente retorna `200`; `GET /escala` deixa de listá-la; repetir o `DELETE` retorna `404`.

---

### P1: Aba "Escala" no front (grade 7×N) ⭐ MVP

**User Story**: Como recepção, quero clicar numa célula da grade para adicionar um aluno e clicar num "✕" ao lado do nome para tirá-lo, sem sair da tela.

**Why P1**: A feature só entrega valor com a tela; o back sozinho não fecha o vertical slice.

**Acceptance Criteria**:

1. WHEN a equipe abre a aba "Escala" THEN o front SHALL carregar a grade e a lista de alunos ativos da clínica numa só passada, exibindo estado de carregamento (`.loading`/`.spinner`).
2. WHEN a equipe clica numa célula THEN o front SHALL abrir a seleção de aluno (combo com os alunos ativos, alfabético), ocultando os que já estão naquele horário.
3. WHEN a equipe confirma o aluno THEN o front SHALL chamar `POST /escala` e atualizar a célula.
4. WHEN a equipe clica no "✕" de um nome THEN o front SHALL pedir confirmação e chamar `DELETE`, atualizando a célula.
5. WHEN a clínica não tem aluno cadastrado THEN o front SHALL orientar a cadastrar pacientes antes (a grade fica sem o que matricular).
6. WHEN a tela é aberta em celular THEN a grade SHALL continuar utilizável — a tabela rola na horizontal e a coluna de horário fica fixa (7 colunas não cabem na largura de um telefone).
7. WHEN um erro de API acontece THEN o front SHALL exibir a mensagem no bloco `.erro` sem perder o estado da tela.

**Independent Test**: Na aba Escala, clicar na célula "Segunda / 07:00", escolher um aluno, ver o nome aparecer na célula; recarregar a página e o nome continuar lá; clicar no "✕" e ele sumir.

---

### P2: Grade sempre coerente com o cadastro de pacientes

**User Story**: Como recepção, quero que a grade nunca mostre aluno que foi removido do cadastro nem nome desatualizado, para não marcar aula para quem não existe mais.

**Why P2**: Higiene do dado; a grade já é utilizável antes disso.

**Acceptance Criteria**:

1. WHEN um paciente é removido (soft delete) DEPOIS de matriculado THEN o sistema SHALL **omitir** as matrículas dele da resposta de `GET /escala`.
2. WHEN um paciente é renomeado DEPOIS de matriculado THEN o sistema SHALL exibir o **nome atual** na grade (não o snapshot gravado na matrícula).
3. WHEN o snapshot é a única fonte disponível THEN o sistema SHALL usá-lo como fallback.

**Independent Test**: Matricular um aluno, removê-lo em `/pacientes`, e `GET /escala` não o lista mais; renomear outro e a grade mostra o nome novo.

---

## Edge Cases

- WHEN `dia` não está entre 1 e 7 THEN o sistema SHALL retornar `400` (1 = segunda … 7 = domingo, padrão ISO).
- WHEN `hora` não está no formato `HH:MM` 24h válido (`07:00`, `19:30`) THEN o sistema SHALL retornar `400`.
- WHEN `hora` vem sem zero à esquerda (`7:00`) THEN o sistema SHALL rejeitar com `400` — o zero é o que garante que a ordem alfabética do SK seja a ordem cronológica.
- WHEN `pacienteId` vem vazio/ausente THEN o sistema SHALL retornar `400`.
- WHEN campos desconhecidos são enviados THEN o sistema SHALL ignorá-los (não persistir lixo).
- WHEN o mesmo aluno é matriculado em **vários** horários THEN o sistema SHALL aceitar (é o caso normal: seg+qua às 7h).
- WHEN existe matrícula num horário fora da lista fixa do front THEN o front SHALL criar a linha para ele mesmo assim (nenhum aluno invisível).
- WHEN a clínica tem muitas matrículas THEN o repositório SHALL paginar (`LastEvaluatedKey`) — a grade nunca trunca em silêncio.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ESC-01 | P1: Ver a grade da semana (`GET /escala`, ordenada) | E2, E3, F1 | Implementing |
| ESC-02 | P1: Persistência PK/SK na partição da clínica (`ESCALA#<dia>#<hora>#<pacienteId>`) | E2 | Implementing |
| ESC-03 | P1: Matricular aluno num dia+horário | E1, E3, F1 | Implementing |
| ESC-04 | P1: Matrícula duplicada → 409 | E2, E3 | Implementing |
| ESC-05 | P1: Remover aluno do horário (remoção física) | E2, E3, F1 | Implementing |
| ESC-06 | P1: Paciente inexistente/removido/de outra clínica → 404 | E3 | Implementing |
| ESC-07 | Edge cases de validação (`dia` 1..7, `hora` HH:MM) → 400 | E1, E3 | Implementing |
| ESC-08 | Isolamento multi-tenant (não vazar entre clínicas) | E2, E3 | Implementing |
| ESC-09 | P2: Nome ao vivo + matrículas órfãs omitidas | E3 | Implementing |
| ESC-10 | P1: Front — aba Escala (grade 7×N, adicionar/remover, contagem, mobile) | F1 | Implementing |
| ESC-11 | Paginação da leitura da grade (`LastEvaluatedKey`) | E2 | Implementing |

**ID format:** `ESC-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 11 total, 11 mapped to tasks, 0 unmapped ✅ — back coberto por 75 testes (suíte 294);
vira **Verified** após o deploy + smoke-test e o teste da aba no browser.

---

## Data Model (referência AD-005 / AD-007)

Item de matrícula na tabela única, **na partição de nível clínica** — a mesma onde já vivem
`SK=METADATA` (nome da clínica) e `SK=APARELHO#<id>` (catálogo):

```
PK = CLINIC#<clinicId>
SK = ESCALA#<dia>#<hora>#<pacienteId>      ex.: ESCALA#1#07:00#a3f2-…
Atributos:
  dia           (int 1..7 — 1 = segunda … 7 = domingo, padrão ISO)
  hora          (string "HH:MM", 24h, com zero à esquerda)
  pacienteId    (string — id do paciente da própria clínica)
  pacienteNome  (string — snapshot do nome no momento da matrícula; exibição usa o nome ao vivo)
  clinicId      (string)
  criadoEm      (ISO timestamp)
```

**Por que este desenho:**

- **A grade inteira sai de 1 Query**: `PK=CLINIC#<clinicId>` + `SK begins_with "ESCALA#"`. O SK
  ordena `dia` → `hora` → `pacienteId`, ou seja, **o resultado já vem na ordem de renderização**
  (a ordenação final por nome dentro da célula é feita na aplicação).
- **Zero mudança de infra**: nenhuma tabela nova, nenhum GSI novo, nenhum atributo indexado novo →
  o deploy é **só código Lambda + front** (aditivo, mesmo perfil de risco de `imagens-paciente`).
  `src/requirements.txt` não muda, então o atalho de deploy sem Docker continua válido.
- **Duplicata é impossível por construção**: aluno+dia+hora *é* a chave. `put_item` com
  `ConditionExpression=attribute_not_exists(PK)` transforma a tentativa em `409`, sem linha repetida.
- **Sem corrida de escrita**: cada matrícula é um item próprio — duas pessoas mexendo na grade ao
  mesmo tempo nunca sobrescrevem uma à outra (o que aconteceria com um item-por-horário guardando
  uma lista de alunos, via read-modify-write).
- **Não colide com nada**: `ESCALA#`, `APARELHO#` e `METADATA` convivem na mesma partição; a PK de
  paciente é mais longa (`CLINIC#<clinicId>#CLIENT#<id>`), como `repository_aparelho.py` já documenta.
- **`hora` com zero à esquerda é regra, não estilo**: `"07:00"` ordena antes de `"19:00"`
  alfabeticamente; `"7:00"` quebraria a ordem cronológica do SK.

**Remoção física (desvio consciente da convenção):** o resto do sistema usa soft delete
(`ativo=False`) porque guarda **histórico** (paciente, aula, avaliação). A escala é **estado
atual**, não histórico — o histórico de quem realmente treinou vive nos itens `SESSION#`. Com
soft delete, a partição acumularia lixo para sempre e "tirar e recolocar o aluno no mesmo horário"
falharia contra a condição de duplicata (o item inativo ainda ocuparia a chave). Portanto:
`delete_item` de verdade.

**Nome do aluno:** a matrícula guarda `pacienteNome` como snapshot, mas o `GET /escala` **resolve
o nome ao vivo** cruzando com `PacienteRepository.list_ativos()` (que o endpoint já consulta para
descartar matrículas órfãs). Assim renomear um paciente não deixa nome velho na grade, e um
paciente removido some da escala sem precisar de cascata na remoção — a grade se auto-limpa.

**Origem do `clinicId`:** `get_clinic_id` (claim `custom:clinicId` do token — AD-012).

**Volume:** 7 dias × ~16 horários × ~10 alunos ≈ 1.100 itens ≈ 250 KB por clínica. Cabe numa Query,
mas perto o bastante do limite de 1 MB para o repositório **já nascer com o loop de
`LastEvaluatedKey`** (o problema hoje deferido em `PacienteRepository.list_ativos`).

**Endpoints (nível clínica, como `/aparelhos`):**

```
GET    /escala                                → 200 lista (dia, hora, pacienteId, nome)
POST   /escala                                → 201 | 400 | 404 (aluno) | 409 (já matriculado)
DELETE /escala/{dia}/{hora}/{pacienteId}      → 200 | 400 | 404
```

Mover um aluno de horário = `DELETE` + `POST` pelo front (não é atômico; no volume de uma clínica
é aceitável — se virar problema, vira um `TransactWriteItems`).

**Lista fixa de horários (front, como AD-011):** `06:00` a `21:00` de hora em hora. O back **não**
valida contra essa lista (aceita qualquer `HH:MM` válido) e o front acrescenta às linhas qualquer
horário que já tenha matrícula — mudar a lista fixa nunca esconde um aluno.

---

## Success Criteria

- [ ] A recepção vê a semana inteira numa tela: 7 colunas (seg–dom), horários nas linhas, alunos nas células com contagem.
- [ ] Dá para matricular e desmatricular um aluno direto na grade, e a mudança persiste após recarregar.
- [ ] O mesmo aluno pode ter vários horários; o mesmo aluno no mesmo horário é recusado (409).
- [ ] Escala de outra clínica nunca aparece nem é acessível; aluno inexistente na clínica retorna 404.
- [ ] Paciente removido do cadastro some da grade; paciente renomeado aparece com o nome novo.
- [ ] A grade é utilizável no celular (rolagem horizontal, coluna de horário fixa).
- [ ] Todos os requisitos (ESC-01..11) cobertos por teste (back) e verificados no front.
- [ ] Deploy **sem alteração de infraestrutura**: `ClinicaTable` e Cognito não são tocados.
