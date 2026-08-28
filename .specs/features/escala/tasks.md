# Tasks — Escala Semanal (Grade de Horários)

**Status:** 🚧 Em implementação. Feature **espelha `cadastro-aparelhos`** (recurso de nível clínica,
`PK=CLINIC#<clinicId>`) com duas diferenças conscientes: a chave é **composta**
(`SK=ESCALA#<dia>#<hora>#<pacienteId>`, sem uuid — o par aluno+horário já é único) e a remoção é
**física**, não soft delete (a escala é estado atual, não histórico — ver spec, "Remoção física").

**Ordem:** backend primeiro (E1→E2→E3), front depois (F1). Deploy ao fim, no terminal do usuário.

**Gate por task:** `.\.venv\Scripts\python.exe -m pytest -q` verde (sem regressão na suíte existente).

**Dependências:** E2 depois de E1; E3 depois de E2; F1 depois de E3.

**⚠️ Infra:** esta feature **não altera `template.yaml`** — nenhuma tabela, GSI, atributo indexado
ou permissão IAM nova. Deploy = código Lambda + front.

---

## E1 — Schemas Pydantic (`src/app/schemas_escala.py`)

**What:** Modelos de validação da matrícula. `dia` inteiro 1..7 (1 = segunda … 7 = domingo, ISO);
`hora` string `HH:MM` 24h **com zero à esquerda** (o zero é o que faz a ordem do SK ser cronológica);
`pacienteId` obrigatório não-vazio.

**Where:** `src/app/schemas_escala.py`, `tests/test_schemas_escala.py`

**Reuses:** `schemas_sessao.py` (helper `_vazio_para_none`, `ConfigDict(extra="ignore")`, validadores
`mode="before"` com mensagem legível → o handler global de `main.py` converte em 400).

**Done when:**
- `EscalaCreate`: `dia: int` (1..7), `hora: str` (`^([01]\d|2[0-3]):[0-5]\d$`), `pacienteId: str` (não-vazio, trimado).
- `EscalaOut`: `dia`, `hora`, `pacienteId`, `nome`, `criadoEm`.
- Mensagens de erro em PT-BR ("dia deve ser um número de 1 (segunda) a 7 (domingo)", "hora deve estar no formato HH:MM").

**Tests:** `dia` 0/8/"seg" → erro; `dia` 1 e 7 aceitos; `hora` `"7:00"`/`"25:00"`/`"07:60"`/`"0700"` → erro;
`hora` `"06:00"`/`"23:59"` aceitos; `pacienteId` vazio/só-espaços → erro; campos desconhecidos ignorados.

**Requirements:** ESC-03 (parte), ESC-07

---

## E2 — Repositório DynamoDB (`src/app/repository_escala.py`)

**What:** Matrícula na partição de nível clínica. `PK=CLINIC#<clinicId>`,
`SK=ESCALA#<dia>#<hora>#<pacienteId>`. Criação com `ConditionExpression=attribute_not_exists(PK)`
(duplicata vira sinal para 409). Listagem por Query + `begins_with`, **com loop de `LastEvaluatedKey`**.
Remoção **física** com `ConditionExpression` (inexistente → `False`).

**Where:** `src/app/repository_escala.py`, `tests/test_repository_escala.py`

**Reuses:** `repository_aparelho.py` como molde (mesma PK de nível clínica, `_pk()`, `_para_*`,
Query por PK + `begins_with` no SK, `_agora_iso`).

**Done when:**
- `_SK_PREFIX = "ESCALA#"`; `_sk(dia, hora, paciente_id)` monta `ESCALA#<dia>#<hora>#<pacienteId>`.
- `create(dia, hora, paciente_id, paciente_nome)` → dict criado; `None` (ou exceção tratada) se já existe.
- `list_all()` → todas as matrículas da clínica, **paginando** até acabar; ordenadas por dia → hora → nome.
- `delete(dia, hora, paciente_id)` → `True`/`False`; apaga fisicamente (`delete_item`).
- `list_all` **não** devolve `SK=METADATA` nem `SK=APARELHO#...` da mesma partição.

**Tests:** persistência PK/SK exata; create duplicado → recusado (item único na tabela);
mesmo aluno em vários horários → aceito; list ordenada por dia→hora→nome; list ignora
`METADATA`/`APARELHO#`; delete remove de verdade (item some da tabela) e delete repetido → `False`;
paginação (>1 página, `LastEvaluatedKey`) devolve tudo; isolamento — repo de outra clínica não vê
nem apaga (list vazia, delete `False`).

**Requirements:** ESC-01, ESC-02, ESC-04, ESC-05, ESC-08, ESC-11

---

## E3 — Router + fiação (`src/app/routers/escala.py`, `main.py`)

**What:** Endpoints de nível clínica. `GET /escala` cruza as matrículas com
`PacienteRepository.list_ativos()`: resolve o **nome ao vivo** e **descarta matrículas órfãs**
(paciente removido). `POST` valida que o aluno é ativo da clínica (404) e trata duplicata (409).
`DELETE` por chave composta.

**Where:** `src/app/routers/escala.py`, `src/app/main.py`, `tests/test_escala.py`

**Reuses:** `routers/aparelhos.py` como molde (router de nível clínica, `get_repository` com
`Depends(get_clinic_id)`); `PacienteRepository.get`/`list_ativos` para 404 e isolamento;
handler global de `RequestValidationError` (`main.py`) para os 400 legíveis.

**Done when:**
- `APIRouter(prefix="/escala", tags=["escala"])`.
- `GET ""` → 200 lista `[{dia, hora, pacienteId, nome, criadoEm}]`, ordenada, sem órfãs, nome ao vivo.
- `POST ""` → 201; 404 `"Aluno não encontrado"`; 409 `"Este aluno já está neste horário"`.
- `DELETE "/{dia}/{hora}/{paciente_id}"` → 200 `{"detail":"Aluno removido do horário"}` | 404 `{"detail":"Matrícula não encontrada"}`; `dia`/`hora` inválidos → 400.
- `main.py` inclui `escala.router`.

**Tests:** criar 201 + aparece no GET; duplicado → 409; aluno inexistente/de outra clínica → 404;
`dia`/`hora` inválidos → 400 (POST e DELETE); remover → 200 e some do GET; remover de novo → 404;
paciente removido depois de matriculado some do GET (órfã); paciente renomeado aparece com nome novo;
isolamento por `X-Clinic-Id` (escala de outra clínica → lista vazia / 404 no delete);
sem regressão em `/health`, `/pacientes`, `/aparelhos`, `/sessoes`.

**Requirements:** ESC-01, ESC-03, ESC-04, ESC-05, ESC-06, ESC-07, ESC-08, ESC-09

---

## F1 — Front: aba "Escala" (`frontend/`)

**What:** Nova aba **Escala** na navegação. Tabela com **7 colunas** (Segunda…Domingo) e linhas de
horário (lista fixa `06:00`–`21:00` de hora em hora, **mais** qualquer horário que já tenha
matrícula). Cada célula lista os alunos com "✕" para remover e um "+" para adicionar (combo com os
alunos ativos, escondendo quem já está no horário). Cabeçalho de cada dia mostra a contagem.

**Where:** `frontend/src/components/Escala.jsx` (novo), `escalaApi` em `frontend/src/api.js`,
aba em `frontend/src/App.jsx`, estilos em `frontend/src/App.css`.

**Reuses:** `pacientesApi.list` (combo de alunos + nomes ao vivo); padrões de `Pilates.jsx`
(estado de carregamento `.loading`/`.spinner`, bloco `.erro`, `primeiroEUltimoNome` de `utils/format.js`);
classes `.card`, `.chip`, `.btn`, `.link.danger` já existentes.

**Done when:**
- Aba "Escala" acessível; grade carrega escala + pacientes em paralelo com spinner.
- Adicionar aluno numa célula (combo), remover com confirmação; ambos refletem na hora.
- Contagem por dia no cabeçalho e por célula quando houver mais de um aluno.
- Clínica sem pacientes → mensagem orientando cadastrar na aba Pacientes.
- **Mobile:** a grade rola na horizontal com a coluna de horário fixa (`position: sticky`) — 7 colunas não cabem no celular.
- ⚠️ `type="button"` em todo botão dentro de form/estado alternante ([[react-button-type-swap-submit]]).

**Requirements:** ESC-10, ESC-01, ESC-03, ESC-05

---

## Deploy — stack `clinica-pilates` + CloudFront (no terminal do usuário)

**What:** Back: `sam build --use-container` + `sam deploy` (ou o atalho sem Docker — `requirements.txt`
não mudou, ver ARQUITETURA.md). Front: `npm run build` + sync S3 com os headers de cache + invalidação.
Smoke-test: matricular, listar, remover, isolamento entre clínicas.

**Done when:** `/escala` no ar; grade funcionando no site; STATE.md/ROADMAP atualizados.

**Requirements:** ESC-01..11 Verified.

---

## Execution Log

| Task | Status | Commit | Notas |
| ---- | ------ | ------ | ----- |
| E1 — Schemas | ✅ Done | — | `dia` 1..7, `hora` `HH:MM` com zero à esquerda; 31 testes |
| E2 — Repositório | ✅ Done | — | `SK=ESCALA#<dia>#<hora>#<pacienteId>`, 409 por condição, delete físico, paginação; 18 testes |
| E3 — Router + fiação | ✅ Done | — | `/escala` GET/POST/DELETE, nome ao vivo + órfãs omitidas; 26 testes (suíte **294**) |
| F1 — Aba Escala | ✅ Done | — | grade 7×16, chips com ✕, modal de adicionar, coluna de horário sticky; `npm run build` OK |
| Deploy | ⏳ | — | usuário (back sem mudança de infra + front no CloudFront) |

**Requirements coverage:** ESC-01..11 implementados; back coberto por 75 testes novos (suíte 219 → **294**).

⚠️ **Front NÃO verificado em browser nesta sessão** — não há Playwright instalado no ambiente
automatizado (só os binários do Chromium), e instalar a dependência mudaria o projeto. Verificação
pendente: `cd frontend; npm run dev` → aba **Escala** contra a API real (esta máquina tem rede).
Ver [[front-verify-mock-sandbox]]. O que **está** verificado: `npm run build` e `npm run lint` sem
erro novo (só o mesmo aviso `exhaustive-deps` que todos os outros componentes já têm), e o contrato
do DELETE com a hora percent-encoded (`07%3A00`), que é a forma que o front envia.
