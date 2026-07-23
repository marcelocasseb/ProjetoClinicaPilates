# Tasks — Cadastro de Avaliação dos Pacientes

Feature espelha a estrutura de `cadastro-aparelhos` (3 tasks: schemas → repositório → router).
Backend primeiro; front numa etapa seguinte. Testes com pytest + moto (fixture `dynamo_table`).

**Gate por task:** `.\.venv\Scripts\python.exe -m pytest -q` verde.

---

## A1 — Schemas Pydantic (`src/app/schemas_avaliacao.py`)

**What:** Modelos de validação da avaliação. Cadastro flexível: nenhum campo clínico
obrigatório; `data` opcional na entrada (default hoje no repositório), validada como
`YYYY-MM-DD` quando informada. `avaliacaoPostural` e `medidas` como submodelos (MAP).

**Where:** `src/app/schemas_avaliacao.py`, `tests/test_schemas_avaliacao.py`

**Reuses:** Padrão de `schemas_aparelho.py` (ConfigDict `extra="ignore"`, validadores
`vazio_para_none`), submodelo aninhado como em `Endereco` (`schemas.py`, AD-009).

**Done when:**
- `AvaliacaoPostural` (MAP): `vistaAnterior`, `vistaLateralDireita`, `vistaLateralEsquerda`, `vistaPosterior` — todos `Optional[str]`, vazio→`None`.
- `Medidas` (MAP): `braco`, `abdomen`, `coxa`, `panturrilha` — `Optional[str]`, vazio→`None`.
- `AvaliacaoBase`: `data` (Optional, valida `YYYY-MM-DD`), `diagnosticoMedico`, `queixaPrincipal`, `hma`, `pressaoArterial`, `fc`, `avaliacaoPostural`, `medidas`, `inspecaoGeral`, `examesComplementares` — todos opcionais; texto vazio→`None`; MAP sem sub-chave preenchida→`None`.
- `AvaliacaoCreate` / `AvaliacaoUpdate` (herdam Base); `AvaliacaoOut` (+ `id`, `pacienteId`, `ativo`, `criadoEm`, `atualizadoEm`).

**Tests:** só-espaços→None; MAP todo-vazio→None; `data` inválida→ValidationError; campos desconhecidos ignorados; `data` válida aceita.

**Requirements:** AVL-03, AVL-10 (parte de AVL-07)

---

## A2 — Repositório DynamoDB (`src/app/repository_avaliacao.py`)

**What:** CRUD do item de avaliação sob a PK do paciente, escopado por `(clinic_id, paciente_id)`.
Soft delete. `data` default = hoje quando ausente. Listagem ordenada por `data` desc na app.

**Where:** `src/app/repository_avaliacao.py`, `tests/test_repository_avaliacao.py`

**Reuses:** Padrão de `repository_aparelho.py` (Query por PK + `begins_with` no SK, `_para_*`,
soft delete via `ativo=False`). PK igual à do paciente (`repository.py`).

**Done when:**
- `PK=CLINIC#<clinicId>#CLIENT#<pacienteId>`, `SK=AVALIACAO#<id>`.
- `create` gera `id`, aplica `data` default hoje, grava `clinicId`/`pacienteId`.
- `get`/`update`/`soft_delete` por id (GetItem direto), respeitando `ativo`.
- `list_ativos` faz Query por PK + `SK begins_with "AVALIACAO#"`, filtra `ativo=True`, ordena por `data` desc (desempate por `criadoEm` desc).

**Tests:** persistência PK/SK; get ativo/inexistente; list ordena desc e omite removidos; list não inclui o `SK=PROFILE` do paciente; update/soft_delete; isolamento — repo de outra clínica/outro paciente não acessa (get/update/soft_delete → None/False).

**Requirements:** AVL-02, AVL-05, AVL-06, AVL-07, AVL-08, AVL-09

---

## A3 — Router + fiação (`src/app/routers/avaliacoes.py`, `main.py`)

**What:** Endpoints REST aninhados no paciente. Valida existência do paciente (404) via
`PacienteRepository` numa dependência de router. `get_clinic_id` (deps.py) dá o tenant.

**Where:** `src/app/routers/avaliacoes.py`, `src/app/main.py`, `tests/test_avaliacoes.py`

**Reuses:** Padrão de `routers/aparelhos.py`; `deps.get_clinic_id`; `PacienteRepository`.

**Done when:**
- `APIRouter(prefix="/pacientes/{paciente_id}/avaliacoes")` com dependência de router que exige paciente ativo (`404 "Paciente não encontrado"`).
- `POST ""` → 201; `GET ""` → lista; `GET/PUT/DELETE "/{avaliacao_id}"` → 200/404 (`"Avaliação não encontrada"`); DELETE 200 `{"detail":"Avaliação removida com sucesso"}`.
- `main.py` inclui `avaliacoes.router`.

**Tests:** criar 201 + data default hoje; criar p/ paciente inexistente 404; obter/editar/remover; listar desc; isolamento por header `X-Clinic-Id`; sem regressão em `/health`, `/pacientes`, `/aparelhos`.

**Requirements:** AVL-01, AVL-04, AVL-05, AVL-06, AVL-07, AVL-08, AVL-09

---

## Depois das tasks
- Rodar suíte completa (deve seguir verde, +N testes).
- Commits atômicos: spec+tasks; A1; A2; A3.
- Deploy: `sam build --use-container` + `sam deploy` + smoke test público.
- Atualizar STATE.md/ROADMAP.md.
