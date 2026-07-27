# Tasks — Registro de Sessões (Aula de Pilates)

**Status:** 🟡 Planejada. Feature **espelha `avaliacao-pacientes`** (recurso aninhado no paciente,
soft delete, fluxo consultar → editar → salvar). Única novidade de modelagem: `aparelhos` é uma
**lista de maps** (`{aparelhoId, nome, treinos[]}`), obrigatória com ≥1 item; o back guarda snapshot
(não revalida contra o catálogo). Backend primeiro (S1→S2→S3), front depois (F1→F2). Deploy ao fim.

**Gate por task:** `.\.venv\Scripts\python.exe -m pytest -q` verde (sem regressão na suíte existente).

**Dependências:** S2 depois de S1; S3 depois de S2; F1 depois de S3 (deployado); F2 depois de F1.

---

## S1 — Schemas Pydantic (`src/app/schemas_sessao.py`)

**What:** Modelos de validação da aula. `aparelhos` obrigatório (≥1 item); cada aparelho é um
submodelo `AparelhoSessao` com `aparelhoId` (opcional — snapshot), `nome` (obrigatório, não-vazio)
e `treinos` (lista de strings, pode ser vazia; textos limpos, vazios descartados). Campos gerais
`data` (opcional, valida `YYYY-MM-DD`), `profissional`, `observacao` — todos opcionais, vazio→None.

**Where:** `src/app/schemas_sessao.py`, `tests/test_schemas_sessao.py`

**Reuses:** `schemas_avaliacao.py` (helper `_vazio_para_none`, `ConfigDict(extra="ignore")`,
validador de `data` `YYYY-MM-DD`, submodelo aninhado como `AvaliacaoPostural`).

**Done when:**
- `AparelhoSessao`: `aparelhoId: Optional[str]`, `nome: str` (obrigatório; só-espaços → erro),
  `treinos: list[str] = []` (cada item trimado; vazios removidos da lista).
- `SessaoBase`: `data` (Optional, valida `YYYY-MM-DD`, vazio→None), `profissional` (Optional, vazio→None),
  `observacao` (Optional, vazio→None), `aparelhos: list[AparelhoSessao]` com `min_length=1`.
- `SessaoCreate` / `SessaoUpdate` (herdam Base); `SessaoOut` (+ `id`, `pacienteId`, `data: str`,
  `ativo`, `criadoEm`, `atualizadoEm`).

**Tests:** aula sem aparelho (lista vazia/ausente) → ValidationError; aparelho sem `nome` → ValidationError;
`nome` só-espaços → erro; `treinos` com strings vazias são descartadas; `data` inválida → erro;
`data`/`profissional`/`observacao` vazios → None; campos desconhecidos ignorados; payload válido aceito.

**Requirements:** SES-01 (parte), SES-03, SES-10

---

## S2 — Repositório DynamoDB (`src/app/repository_sessao.py`)

**What:** CRUD do item de aula sob a PK do paciente, escopado por `(clinic_id, paciente_id)`.
`SK=SESSION#<id>`. `data` default = hoje quando ausente. Soft delete. Listagem ordenada por
`data` desc (desempate por `criadoEm` desc) na aplicação. `aparelhos` (lista de maps) persiste
e relê intacto.

**Where:** `src/app/repository_sessao.py`, `tests/test_repository_sessao.py`

**Reuses:** `repository_avaliacao.py` como molde (mesma PK do paciente; `_CAMPOS` whitelist;
Query por PK + `begins_with` no SK; `_para_*`; soft delete via `ativo=False`; `update_item` com
`ExpressionAttributeNames`).

**Done when:**
- `_SK_PREFIX = "SESSION#"`; `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=SESSION#<id>`.
- `_CAMPOS = ("data", "profissional", "observacao", "aparelhos")`.
- `create` gera `id`, aplica `data` default hoje, grava `clinicId`/`pacienteId`; persiste `aparelhos`
  (lista de maps de strings) round-trip.
- `get`/`update`/`soft_delete` por id, respeitando `ativo`.
- `list_ativos`: Query por PK + `SK begins_with "SESSION#"`, filtra `ativo=True`, ordena por `data` desc.

**Tests:** persistência PK/SK; `aparelhos` (lista de maps + `treinos`) round-trip create+update;
get ativo/inexistente; list ordena desc e omite removidos; list **não inclui** `SK=PROFILE` nem
`SK=AVALIACAO#...` da mesma PK; update/soft_delete; isolamento — repo de outra clínica/outro
paciente não acessa (get/update/soft_delete → None/False).

**Requirements:** SES-02, SES-04, SES-05, SES-07, SES-08, SES-09

---

## S3 — Router aninhado + fiação (`src/app/routers/sessoes.py`, `main.py`)

**What:** Endpoints REST aninhados no paciente. Dependência de router exige paciente ativo (404).
`get_clinic_id` (deps.py) dá o tenant. Aula sem aparelho → 400 (via validação do schema, tratada
pelo handler global que já converte erro de validação em 400 legível).

**Where:** `src/app/routers/sessoes.py`, `src/app/main.py`, `tests/test_sessoes.py`

**Reuses:** `routers/avaliacoes.py` como molde (dependência `exigir_paciente`, `get_repository`,
mesmos handlers 201/200/404); `deps.get_clinic_id`; `PacienteRepository`.

**Done when:**
- `APIRouter(prefix="/pacientes/{paciente_id}/sessoes")` com dependência que exige paciente ativo
  (`404 "Paciente não encontrado"`).
- `POST ""` → 201; `GET ""` → lista (ordenada desc); `GET/PUT/DELETE "/{sessao_id}"` → 200/404
  (`"Aula não encontrada"`); DELETE 200 `{"detail":"Aula removida com sucesso"}`.
- `PUT`/`POST` sem aparelho → 400 com mensagem legível (uma aula precisa de ao menos um aparelho).
- `main.py` inclui `sessoes.router`.

**Tests:** criar 201 + `data` default hoje; criar aula sem aparelho → 400; criar p/ paciente
inexistente → 404; obter/editar/remover; listar desc; isolamento por header `X-Clinic-Id`
(aula de outra clínica → 404); sem regressão em `/health`, `/pacientes`, `/aparelhos`, `/avaliacoes`.

**Requirements:** SES-01, SES-04, SES-05, SES-06, SES-07, SES-08, SES-09

---

## Deploy back — stack `clinica-pilates`

**What:** `sam build --use-container` + `sam deploy` (Docker aberto). Smoke-test público:
criar aula com aparelho+treinos, listar/obter, editar, remover, isolamento entre clínicas.
Atualizar STATE.md/ROADMAP (M2 pt3 → COMPLETE no back).

**Done when:** endpoints `/pacientes/{id}/sessoes` no ar; ciclo completo + isolamento OK.

**Requirements:** SES-01..10 (back) Verified.

---

## F1 — Front: aba "Pilates" (registrar aula) (`frontend/`)

**What:** Nova aba "Pilates" na navegação. Fluxo: buscar/selecionar aluno → aula com **data de hoje**
já preenchida → adicionar aparelhos por **combo box** (catálogo ativo da clínica) → para cada aparelho,
seleção múltipla dos **tipos de treino** (lista fixa hardcoded: Membros superiores, Membros inferiores,
Abdômen, Força, Mobilidade) → campos **Observação** e **Profissional** → Salvar. Envia `data` explícita
(fuso local, contorna desvio UTC — igual avaliação).

**Where:** `frontend/src/components/Pilates.jsx` (ou `Sessoes.jsx`), `sessoesApi` + `aparelhosApi`
(reuso) em `api.js`, entrada de aba no `App.jsx`.

**Reuses:** `Avaliacoes.jsx` (busca de aluno, envio de `data` explícita, chamadas de API);
`aparelhosApi.list` já existente para o combo; máscaras/padrões do front atual.
Constante `TIPOS_TREINO` hardcoded no front.

**Done when:**
- Aba "Pilates" acessível; combo lista aparelhos ativos da clínica; dá pra adicionar vários,
  cada um com seus treinos (multi-seleção); remover aparelho da lista antes de salvar.
- Combo vazio → mensagem orientando cadastrar aparelhos.
- Salvar cria a aula; erro de "aula sem aparelho" bloqueado no front (não deixa salvar).
- ⚠️ Usar `type="button"` + `key` nos botões que alternam estado ([[react-button-type-swap-submit]]);
  `lang=pt-BR`/`notranslate` já no index (evita quebra por tradução do Chrome, [[browser-autotranslate-front]]).

**Requirements:** SES-11 (parte), SES-01, SES-03

---

## F2 — Front: consulta datada + editar/salvar/remover (`frontend/`)

**What:** Na aba Pilates, ao selecionar um aluno, listar as **aulas por data** (mais recente primeiro,
como na tela de avaliações). Clicar numa data abre a aula **em leitura** (`<fieldset disabled>`);
**Editar** destrava e vira **Salvar**; ao salvar edição, volta pra leitura mantendo os dados.
Remover (soft delete) com confirmação.

**Where:** mesmos arquivos de F1.

**Reuses:** fluxo consultar → editar → salvar de `Avaliacoes.jsx` (F2 da avaliação).

**Done when:**
- Lista de aulas datadas do aluno; abrir em leitura; Editar/Salvar; Remover.
- Publicado no CloudFront com os headers de cache corretos (assets imutáveis + `index.html` no-cache
  + invalidação — ver STATE.md).

**Requirements:** SES-11, SES-05, SES-07, SES-08

---

## Execution Log

| Task | Status | Commit | Notas |
| ---- | ------ | ------ | ----- |
| S1 — Schemas | ⬜ Pending | — | `aparelhos` lista de maps, min 1 |
| S2 — Repositório | ⬜ Pending | — | `SK=SESSION#<id>`, snapshot aparelhos |
| S3 — Router aninhado | ⬜ Pending | — | `/pacientes/{id}/sessoes`, 404/400 |
| Deploy back | ⬜ Pending | — | smoke-test público |
| F1 — Aba Pilates (registrar) | ⬜ Pending | — | combo aparelhos + treinos hardcode |
| F2 — Consulta/editar/remover | ⬜ Pending | — | fluxo leitura→editar→salvar |

**Requirements coverage:** SES-01..11 mapeados. Atualizar status para Verified conforme execução.
