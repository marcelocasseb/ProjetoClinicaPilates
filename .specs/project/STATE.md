# State

**Last Updated:** 2026-07-21
**Current Work:** Feature `cadastro-pacientes` ✅ CONCLUÍDA, DEPLOYADA e **refatorada para multi-tenant**. Refactor R1–R4 (2026-07-21) aplicou: `cpf` validado (AD-008), `endereco` como MAP (AD-009) e **multi-tenancy por clínica** (AD-007) — chave `PK=CLINIC#<clinicId>#CLIENT#<clientId>` + GSI1 de listagem. 61 tests verdes; deploy OK (GSI adicionado à tabela); smoke-test público confirmou cpf/endereço e **isolamento entre clínicas**. **Decisão da listagem: cliente-na-PK + GSI** (preserva o padrão AD-005 de "ficha do paciente = 1 Query"). **B-003 RESOLVIDO.** PRÓXIMO PASSO: **Milestone M2**, dividido em 2 features na ordem: (1) **Cadastro de Aparelhos** por clínica (`PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>` — nível clínica, listagem por Query direto sem GSI), depois (2) **Registro de Sessões** (`SK=SESSION#<data>` sob o paciente, referenciando aparelhos do catálogo com snapshot id+nome). ✅ **Feature `cadastro-aparelhos` CONCLUÍDA no código** (A1 schemas, A2 repositório, A3 endpoints) — APR-01..09 Verified, 96 tests verdes. CRUD `/aparelhos` por clínica (`PK=CLINIC#<clinicId>`, `SK=APARELHO#<id>`, listagem por Query sem GSI, isolamento testado). `get_clinic_id` extraído p/ `src/app/deps.py` (compartilhado com pacientes). ⏭️ PRÓXIMO na Rota do Demo: **deployar aparelhos** (`sam build --use-container; sam deploy`) e depois **Login simples + Front leve** pro demo. Sessões e Cognito ficam pós-demo.

**Recursos AWS provisionados (stack `clinica-pilates`, us-east-1):**
- API base: https://8f1ffym997.execute-api.us-east-1.amazonaws.com
- Tabela DynamoDB: `clinica-pilates-ClinicaTable-8YQAEIFAKZGE` (PK/SK, on-demand)
- Lambda: `clinica-pilates-ClinicaApiFunction-3huxBJXkP1qi`
- Redeploy: `sam build --use-container; sam deploy` (config em samconfig.toml)

**Onde paramos (retomar aqui):**
- ✅ Projeto inicializado (PROJECT/ROADMAP/STATE), commit `621b608`
- ✅ Planejamento da infra + TESTING.md commitados, commit `8e855b6`
- ✅ Decisão de banco: DynamoDB single-table (AD-005)
- ✅ Spec `cadastro-pacientes` escrita (PAC-01..09) — aguarda infra
- ✅ Spec + tasks `infra-base-sam` (INFRA-01..06, T1..T6)
- ✅ Convenção de testes: pytest + moto, cobertura pragmática (TESTING.md)
- ✅ **T1 scaffold done** (`6d3fc75`): src/app, tests/, requirements, pyproject, .gitignore; venv `.venv` criado, deps instaladas OK no Python 3.14
- ✅ **T2 done**: `src/app/main.py` (FastAPI + GET /health) + `tests/test_health.py` (2 testes verdes)
- ✅ **T3 done**: `src/app/handler.py` (Mangum) + `tests/test_handler.py` (smoke test v2, 200) — 3 testes no total
- ✅ **T4+T5 done**: `template.yaml` (Lambda py3.13 + HTTP API proxy + CORS + DynamoDB PK/SK on-demand + IAM DynamoDBCrudPolicy + TABLE_NAME). Validado: `sam validate --lint` OK
- ✅ **T6 done**: `sam build --use-container` + `sam deploy` → stack `clinica-pilates` no ar; `/health` → `{"status":"ok"}`
- ✅ SAM CLI 1.163.0 instalado → **B-001 resolvido**; Docker build → **B-002 resolvido** (AD-006)
- ✅ **Feature `infra-base-sam` COMPLETA**
- ✅ **Feature `cadastro-pacientes` COMPLETA no código** (tasks.md T1–T4):
  - T1: `src/app/schemas.py` (Pydantic — nome obrigatório, email regex, dataNascimento YYYY-MM-DD, vazios→None, extra ignorado)
  - T2: `src/app/repository.py` (`PacienteRepository` — create/get/list_ativos/update/soft_delete; PK=CLIENT#id, SK=PROFILE; testes moto)
  - T3: `src/app/routers/pacientes.py` (POST /pacientes, GET /pacientes/{id}) fiado em `main.py` via `include_router`
  - T4: mesmo router — GET /pacientes (listar ativos), PUT /pacientes/{id}, DELETE /pacientes/{id} (soft delete, 204)
  - Suíte: 45 tests verdes (`.\.venv\Scripts\python.exe -m pytest -q`)
  - Ajuste pós-review: validação retorna 400 com msg legível (`nome é obrigatório`, `email inválido`); DELETE retorna 200 `{"detail":"Paciente removido com sucesso"}` / 404 `{"detail":"Paciente não encontrado"}`
  - ✅ **DEPLOYADO** (`sam build --use-container` + `sam deploy`): `/pacientes` no ar; smoke-test público OK
- ✅ **Milestone M1 CONCLUÍDO**
- ✅ **Refactor multi-tenant + cpf + endereço CONCLUÍDO e DEPLOYADO** (2026-07-21, R1–R4):
  - R1: `schemas.py` — `cpf` validado (AD-008) + submodelo `Endereco` (AD-009) — commit `2137b16`... (ver git)
  - R2/R3/R4: chave `CLINIC#<clinicId>#CLIENT#<id>`, GSI1 (`template.yaml` + `conftest.py`), `get_clinic_id` (header `X-Clinic-Id` / default; token no M3), isolamento testado
  - Chave multi-tenant escolhida: **cliente-na-PK + GSI** (não clínica-na-PK) — preserva "ficha do paciente = 1 Query por PK" (AD-005). B-003 resolvido.
- ⏭️ FAZER A SEGUIR: **M2 — Registro de Sessões e Aparelhos**. Escrever a spec (endpoints de sessão por paciente, `SK=SESSION#<data>` com lista denormalizada de aparelhos/exercícios), **sob a mesma PK multi-tenant** (`CLINIC#<clinicId>#CLIENT#<clientId>`). Rodar app local: `TABLE_NAME=clinica-pilates-ClinicaTable-8YQAEIFAKZGE .venv\Scripts\python -m uvicorn app.main:app --app-dir src --reload` (header `X-Clinic-Id` opcional). Deploy: `sam build --use-container; sam deploy` (Docker aberto).

**Ambiente local:** venv em `.venv` (Python 3.14). Testes: `.\.venv\Scripts\python.exe -m pytest -q`.
**SAM CLI:** não está no PATH da sessão automatizada; caminho completo = `C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd` (no terminal do usuário, `sam` funciona direto).

---

## Recent Decisions (Last 60 days)

### AD-009: Endereço do paciente como MAP (objeto aninhado), preenchido via CEP no front (2026-07-21)

**Decision:** O endereço do paciente será um **MAP** (objeto aninhado) no item DynamoDB, não um campo string único nem vários atributos soltos. Submodelo Pydantic `Endereco`:
```
endereco: { cep, logradouro, numero, complemento, bairro, cidade, uf }
```
Campo **opcional**. A consulta ao CEP (ViaCEP) é feita **no front-end** — o back apenas recebe e armazena o objeto já montado (não chama ViaCEP).
**Reason:** Casa 1-para-1 com o retorno do ViaCEP (`logradouro`, `bairro`, `localidade`, `uf`) e com o formulário do front; mantém o endereço coeso e fácil de exibir/editar; DynamoDB suporta Map nativo. Campo único perde estrutura; atributos soltos poluem o item.
**Trade-off:** Front assume a responsabilidade da consulta de CEP (aceito — evita chamada externa na Lambda).
**Impact:** `schemas.py` ganha submodelo `Endereco` (troca `endereco: Optional[str]` por `Optional[Endereco]`). Aplicar junto com o refactor multi-tenant (B-003).

### AD-008: CPF do paciente — opcional e validado (2026-07-21)

**Decision:** Adicionar `cpf` ao paciente. Campo **opcional**, mas **validado** quando informado (11 dígitos + dígitos verificadores, não só tamanho). Armazenado **normalizado** (só números); o front formata na exibição.
**Reason:** Mantém a regra de cadastro rápido (só `nome` obrigatório) sem abrir mão da integridade do dado quando o CPF é preenchido.
**Trade-off:** Não impede duplicidade por ora.
**Impact:** `schemas.py` ganha campo `cpf` + validador de dígitos verificadores. **Futuro:** CPF é bom candidato a **único por clínica** (impedir cadastro duplicado) — avaliar quando o multi-tenant existir. Aplicar junto com o refactor multi-tenant (B-003).

### AD-007: Multi-tenancy modelo pool — `clinicId` na PK (planejado, aplicar antes do M2) (2026-07-20)

**Decision:** O sistema servirá **várias clínicas** (multi-tenant) na mesma tabela/stack, modelo **pool** (compartilhado, isolamento lógico). Cada registro carrega o `clinicId` no início da partition key:
- Perfil: `PK=CLINIC#<clinicId>#CLIENT#<clientId>`, `SK=PROFILE`
- Demais itens do cliente: mesma PK, `SK=SESSION#<data>` / `MEASURE#<data>` / etc.
- Listar pacientes de uma clínica: via **GSI** (`GSI1PK=CLINIC#<clinicId>`) — substitui o `Scan` atual por `Query` escopado.

**Isolamento (o ponto crítico de segurança):** toda query filtra pelo `clinicId` **derivado do token do login** (custom claim do Cognito, M3) — **NUNCA** do corpo/params da requisição. Assim, usuário da clínica 1 pedindo id da clínica 2 → busca só dentro de `CLINIC#1` → 404. É o token + filtro server-side que garantem o isolamento, não a URL.

**Reason:** Habilita vender pra 1, 10 ou 500 clínicas sem re-arquitetura (DynamoDB e Lambda escalam sozinhos; chave por paciente já espalha a carga). Custo continua por uso. Padrão de mercado para SaaS serverless.
**Trade-off:** Isolamento lógico (não físico) — exige disciplina de sempre filtrar por tenant. Cresce a necessidade de features de produto (onboarding de clínica, billing por clínica, super-admin), que são módulos por cima, não re-arquitetura.
**Impact:** Revisa a convenção de chaves do AD-005 (prefixa `CLINIC#<clinicId>#`). Deve ser aplicado **antes** do M2 para evitar migração de dados (ver B-003). Até o Cognito (M3), usar um `clinicId` "default" fixo já deixa o modelo pronto.

### AD-001: Backend em FastAPI + Mangum (2026-07-18)

**Decision:** Usar FastAPI com adaptador Mangum em uma única Lambda com roteamento interno.
**Reason:** Validação via Pydantic, docs automáticas, alinhado à sugestão da especificação original.
**Trade-off:** ZIP um pouco maior que Flask.
**Impact:** Handler Lambda usa Mangum; rotas definidas no app FastAPI.

### AD-002: IaC com AWS SAM (2026-07-18)

**Decision:** Provisionar a infraestrutura com AWS SAM.
**Reason:** Menor complexidade para uma stack puramente serverless (Lambda + API Gateway + DynamoDB); usuário delegou a escolha.
**Trade-off:** Menos flexível/multi-cloud que Terraform, menos poderoso que CDK.
**Impact:** Template `template.yaml` do SAM define os recursos; deploy via `sam deploy`.

### AD-003: Escopo do v1 restrito a CRUD de Pacientes (2026-07-18)

**Decision:** v1 entrega apenas o CRUD de pacientes + infraestrutura base. Sessões/aparelhos, Cognito e uploads ficam para milestones seguintes.
**Reason:** Escolha do usuário no questionário de inicialização — reduzir escopo inicial.
**Trade-off:** O core do produto (registro de aparelhos por sessão) só chega no M2.
**Impact:** ROADMAP organizado em M1–M4.

### AD-004: Frontend especificado à parte via spec "impecable" (2026-07-18)

**Decision:** A stack e a implementação do frontend serão definidas em uma especificação separada chamada "impecable".
**Reason:** Preferência do usuário — criar especificações próprias para o front.
**Trade-off:** Framework de frontend fica indefinido no PROJECT.md por ora.
**Impact:** M4 depende dessa spec; hospedagem já definida como S3 + CloudFront.

### AD-006: Build da Lambda via `sam build --use-container` (Docker como ferramenta de build) (2026-07-18)

**Decision:** Usar Docker apenas como ferramenta de build local (`sam build --use-container`) para gerar wheels Linux (manylinux) das dependências nativas. A entrega continua sendo ZIP.
**Reason:** `pydantic-core` (dep do FastAPI) é nativo/compilado; build no Windows gera wheel incompatível com o Lambda (Linux). O container replica o ambiente do Lambda e resolve as wheels corretas. Python local é 3.14, sem 3.13 no PATH — o container também elimina esse requisito.
**Trade-off:** Precisa do Docker Desktop rodando para buildar. Não fere a decisão original ("sem Docker" referia-se ao modelo de entrega — ZIP em vez de imagem container/Fargate).
**Impact:** Fluxo de deploy: abrir Docker Desktop → `sam build --use-container` → `sam deploy`. Resolve o restante do B-002.

### AD-005: Manter DynamoDB com single-table design centrado no cliente (2026-07-18)

**Decision:** Confirmado DynamoDB (não migrar para relacional). Modelo single-table onde tudo pende do cliente. Convenção de chaves compartilhada por todas as features:
- Perfil: `PK=CLIENT#<id>`, `SK=PROFILE`
- Medida corporal: `PK=CLIENT#<id>`, `SK=MEASURE#<ISO-date>`
- Pressão arterial: `PK=CLIENT#<id>`, `SK=BP#<ISO-date>`
- Aula/sessão: `PK=CLIENT#<id>`, `SK=SESSION#<ISO-date>` (com lista denormalizada de exercícios/procedimentos)
- Consulta: `PK=CLIENT#<id>`, `SK=CONSULT#<ISO-date>`

> ⚠️ **ATUALIZADO por AD-007 (multi-tenant, 2026-07-21):** a PK agora carrega o prefixo da clínica —
> `PK=CLINIC#<clinicId>#CLIENT#<clientId>`. Os SKs acima permanecem iguais. Toda feature nova (M2+)
> deve usar essa PK. Listagem de pacientes de uma clínica via GSI1 (`GSI1PK=CLINIC#<clinicId>`).
- Catálogo de exercícios: `PK=EXERCISE`, `SK=EX#<id>`
**Reason:** Os dados são centrados no cliente e em série temporal (medidas, pressão, aulas, consultas). "Última aula" e "evolução do paciente" são queries nativas do DynamoDB (Query por PK + range no SK). Schema-less facilita adicionar novos tipos (ex: consultas) sem migração. Mantém meta de custo $0–5/mês.
**Trade-off:** Relatórios cruzados entre pacientes (agregações da clínica inteira) exigem GSI ou exportação — aceito por ora; o sistema é uma ficha por paciente.
**Impact:** Todas as feature specs referenciam esta convenção de chaves. Reverte a avaliação anterior que considerava Aurora/relacional.

---

## Active Blockers

### B-003: Ajustar convenção de chaves para multi-tenant ANTES do M2 — ✅ RESOLVIDO (2026-07-21)

**Discovered:** 2026-07-20 (dúvida do usuário sobre vender para várias clínicas)
**Impact:** O `clinicId` faz parte da partition key (AD-007). Sem isso antes do M2, haveria migração de dados depois.
**Resolution:** Refactor R1–R4 aplicado e deployado em 2026-07-21. Chave `PK=CLINIC#<clinicId>#CLIENT#<clientId>` + GSI1 de listagem por clínica. Estratégia escolhida: **cliente-na-PK + GSI** (preserva "ficha do paciente = 1 Query por PK", AD-005) — descartado o clínica-na-PK. `clinicId` vem de `get_clinic_id` (header `X-Clinic-Id` / default hoje; token Cognito no M3). Junto foram aplicados AD-008 (cpf) e AD-009 (endereço MAP). 61 tests + smoke-test público de isolamento OK. M2 pode ser construído já multi-tenant.

### B-001: SAM CLI não instalado — ✅ RESOLVIDO (2026-07-18)

**Discovered:** 2026-07-18
**Impact:** Bloqueava `sam build`/`sam deploy` da feature Infra Base.
**Resolution:** SAM CLI 1.163.0 instalado (via winget). Deploy destravado. Pendente ainda: confirmar credenciais AWS (`aws sts get-caller-identity`) antes da T6.

### B-002: Python local 3.14 vs runtime Lambda — ✅ RESOLVIDO (via AD-006)

**Discovered:** 2026-07-18
**Impact:** `sam build` local falhou: (1) sem python3.13 no PATH; (2) mesmo com ele, wheels Windows do pydantic-core não rodam no Lambda (Linux).
**Resolution:** Decidido (AD-006) usar `sam build --use-container` — o container Linux gera as wheels manylinux corretas e dispensa python3.13 local. Pré-requisito: Docker Desktop rodando (instalado v29.3.1, precisa estar aberto).

---

## Lessons Learned

_Nenhuma ainda._

---

## Quick Tasks Completed

| #   | Description | Date | Commit | Status |
| --- | ----------- | ---- | ------ | ------ |

---

## Deferred Ideas

- [ ] Upload de fotos/laudos/anexos por paciente (S3) — Captured during: inicialização
- [ ] Relatórios de uso de aparelhos — Captured during: inicialização
- [ ] **Papéis/permissões dentro da clínica (roles via Cognito groups)** — ex.: recepcionista vê pacientes mas não edita; fisioterapeuta vê tudo. Camada ADICIONAL à do `clinicId` (que já isola entre clínicas). Refinamento pós-M3. — Captured during: discussão multi-tenant (2026-07-21)
- [ ] **Onboarding de nova clínica** (self-service) — tela que cria o `clinicId` + primeiro usuário admin da clínica. Necessário para virar SaaS de fato. — Captured during: discussão multi-tenant (2026-07-21)

---

## Todos

- [ ] Especificar frontend via spec "impecable" (M4)
- [ ] **M3 (login/Cognito) — trocar a fonte do `clinicId`:** hoje `get_clinic_id()` (em `src/app/routers/pacientes.py`) lê o header temporário `X-Clinic-Id` (andaime inseguro). No M3, passar a extrair o `clinicId` do **token** do usuário logado (custom claim do Cognito, gravado na conta na criação). **Só essa função muda** — endpoints e repositório continuam iguais. Autenticação (validar assinatura/expiração do token) fica no API Gateway + Cognito, antes da Lambda. Duas camadas: autenticação ("quem é você" = Cognito) + autorização/isolamento ("só a sua clínica" = filtro pelo `clinicId` do token, já pronto).

---

## Preferences

**Model Guidance Shown:** never
