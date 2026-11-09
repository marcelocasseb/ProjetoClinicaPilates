# Relatórios Tasks

**Design**: `.specs/features/relatorios/design.md`
**Status**: Draft

---

## Execution Plan

### Fase 1: Back, base (paralelo OK)

```
T1 [P]   mensalidades.py (extração)
T2 [P]   PacienteRepository.list_todos
T3 [P]   repository_atendimento.py
T4       relatorios.py: base + financeiro ──→ T5 alunos ──→ T6 ocupação ──→ T7 atendimento
```
T1, T2, T3 e T4 não dependem entre si. T4→T7 são sequenciais porque mexem no mesmo arquivo.

### Fase 2: Back, API (sequencial)

```
T1,T2,T3,T7 ──→ T8 schemas_relatorio ──→ T9 router /relatorios (+ main)
```

### Fase 3: Front (paralelo parcial)

```
T9 ──→ T10 relatoriosApi
T11 [P] graficos.jsx            (não depende do back)
T10,T11 ──→ T12 RelFinanceiro ─┐
            T13 RelAlunos     ─┤  (T12–T15 [P] entre si)
            T14 RelOcupacao   ─┤
            T15 RelAtendimento─┘──→ T16 Relatorios.jsx + aba App ──→ T17 impressão ──→ T18 fechamento (P2)
```

### Fase 4: Verificação e entrega (sequencial)

```
T18 ──→ T19 verificação visual + PDF (Playwright mock) ──→ T20 deploy back+front + smoke + docs
```

---

## Task Breakdown

### T1: Extrair `calcular_mensalidades` [P]
**What**: mover a lógica de `mensalidades_do_mes` (e `_status`) para `src/app/mensalidades.py::calcular_mensalidades(alunos, planos, lancamentos_competencia, escala)`. O router financeiro passa a chamar a função.
**Where**: `src/app/mensalidades.py` (novo), `src/app/routers/financeiro.py`
**Depends on**: None · **Reuses**: código atual do router · **Requirement**: REL-06
**Done when**: [ ] router só busca dados e delega · [ ] `test_mensalidades.py` inalterado e verde · [ ] teste unit novo da função pura (aluno pago/parcial/aberto/isento/sem plano)
**Tests**: unit · **Gate**: quick

### T2: `PacienteRepository.list_todos()` [P]
**What**: Query no GSI1 sem filtro de `ativo`, paginada, devolvendo ativos e removidos.
**Where**: `src/app/repository.py`, `tests/test_repository.py`
**Depends on**: None · **Reuses**: `list_ativos` · **Requirement**: REL-07, REL-13
**Done when**: [ ] devolve ativos e removidos (com `ativo` e `atualizadoEm`) · [ ] não vê pacientes de outra clínica · [ ] paginação coberta (moto com vários itens)
**Tests**: unit (moto) · **Gate**: quick

### T3: `repository_atendimento.list_sessoes_periodo` [P]
**What**: Queries em paralelo (ThreadPoolExecutor, 16 workers, client boto3 + TypeDeserializer) das aulas ativas de N alunos com `data` entre `de` e `ate`. Cada item volta com `pacienteId`.
**Where**: `src/app/repository_atendimento.py` (novo), `tests/test_repository_atendimento.py`
**Depends on**: None · **Reuses**: chaves de `repository_sessao.py` · **Requirement**: REL-13, REL-19
**Done when**: [ ] filtra período e `ativo` · [ ] ignora avaliações e imagens sob a mesma PK · [ ] isolamento: ids de outra clínica não retornam nada · [ ] lista vazia de ids devolve `[]` sem chamar o DynamoDB
**Tests**: unit (moto) · **Gate**: quick

### T4: `relatorios.py`: base + financeiro
**What**: `mes_local`, `meses_ate`, `resumo_caixa`, `receita_por_forma`, `resumo_mensalidades`.
**Where**: `src/app/relatorios.py` (novo), `tests/test_relatorios.py`
**Depends on**: None · **Requirement**: REL-03, REL-04, REL-05, REL-06
**Done when**: [ ] `meses_ate` atravessa a virada de ano (2026-02 → 2025-03..2026-02) · [ ] `mes_local("2026-10-01T01:30:00Z") == "2026-09"` · [ ] `cartao` e sem forma rotulados · [ ] pct soma ~100 · [ ] listas vazias dão zeros
**Tests**: unit · **Gate**: quick

### T5: `relatorios.py`: alunos
**What**: `indicadores_alunos`, `evolucao_alunos`, `carteira_planos`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T4 · **Requirement**: REL-07, REL-08, REL-09, REL-10
**Done when**: [ ] novo/saída/ativo-no-fim conforme as regras do design · [ ] aluno criado e removido no mesmo mês conta como novo e como saída, e não como ativo · [ ] planos de removidos fora da carteira · [ ] ticket médio ignora isentos · [ ] distribuição por frequência
**Tests**: unit · **Gate**: quick

### T6: `relatorios.py`: ocupação
**What**: `ocupacao(matriculas, alunos_ativos)`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T5 · **Requirement**: REL-11, REL-12
**Done when**: [ ] contagem por célula · [ ] top 5 ordenado (desempate por dia/hora) · [ ] média só sobre horários ocupados · [ ] fora da escala = ativos sem matrícula · [ ] matrícula órfã ignorada · [ ] grade vazia dá zeros
**Tests**: unit · **Gate**: quick

### T7: `relatorios.py`: atendimento
**What**: `atendimento(sessoes, perfis, mes, meses)`.
**Where**: `src/app/relatorios.py`, `tests/test_relatorios.py`
**Depends on**: T6 · **Requirement**: REL-13, REL-14, REL-15
**Done when**: [ ] total do mês e evolução de 12 meses · [ ] por profissional (por id, nome do snapshot mais recente, "Sem profissional") · [ ] por aluno (inclui aluno removido, com o nome do perfil) · [ ] aparelho conta 1 por aula · [ ] treinos contados · [ ] nome do snapshot preservado
**Tests**: unit · **Gate**: quick

### T8: `schemas_relatorio.py`
**What**: os 4 modelos de saída do design.
**Where**: `src/app/schemas_relatorio.py`
**Depends on**: T7 · **Requirement**: REL-03..15
**Done when**: [ ] modelos batem com as saídas das funções de T4–T7 (validados pelos testes de T9)
**Tests**: unit (coberto via endpoints em T9) · **Gate**: build

### T9: Router `/relatorios` + registro no `main.py`
**What**: 4 GETs com `require_admin` no APIRouter, validação de `?mes=` (inválido ou futuro dá 400; ausente = mês corrente UTC−3).
**Where**: `src/app/routers/relatorios.py` (novo), `src/app/main.py`, `tests/test_relatorios_api.py`
**Depends on**: T1, T2, T3, T8 · **Requirement**: REL-01..15, REL-18
**Done when**: [ ] membro recebe 403 nos 4 · [ ] **isolamento**: dados da clínica B não aparecem na A · [ ] o Financeiro bate com `GET /financeiro/lancamentos` e `/mensalidades` do mesmo mês · [ ] clínica vazia dá 200 com zeros nos 4 · [ ] mês futuro e inválido dão 400 · [ ] suíte inteira verde
**Tests**: unit (moto) · **Gate**: full

### T10: `relatoriosApi` no front
**What**: 4 chamadas em `api.js`.
**Where**: `frontend/src/api.js`
**Depends on**: T9 · **Requirement**: REL-01
**Done when**: [ ] `npm run build` e `npm run lint` sem erro novo
**Tests**: none · **Gate**: build (npm)

### T11: `graficos.jsx` [P]
**What**: `Kpi`, `BarrasMensais`, `Ranking`, `MapaCalor` em SVG/CSS próprios, legíveis em P&B.
**Where**: `frontend/src/components/relatorios/graficos.jsx`, `App.css` (seção `rel-*`)
**Depends on**: None · **Requirement**: REL-04, REL-08, REL-11, REL-13, REL-16 AC4
**Tools**: Skill **dataviz** (carregar antes de escrever)
**Done when**: [ ] valores escritos (não só cor) · [ ] 12 meses cabem a 390 px (rolagem horizontal se preciso) · [ ] build e lint OK
**Tests**: none · **Gate**: build (npm)

### T12–T15: `RelFinanceiro`, `RelAlunos`, `RelOcupacao`, `RelAtendimento` [P]
**What**: um componente de apresentação por arquivo, `({dados, mes})`, com estado vazio e as notas da spec.
**Where**: `frontend/src/components/relatorios/Rel*.jsx`
**Depends on**: T10, T11 · **Requirement**: T12 → REL-03..06 · T13 → REL-07..10 · T14 → REL-11, REL-12 · T15 → REL-13..15
**Tools**: Skill dataviz
**Done when**: [ ] todos os ACs da story renderizados · [ ] estado vazio · [ ] R$ e datas BR · [ ] build e lint OK
**Tests**: none · **Gate**: build (npm)

### T16: `Relatorios.jsx` + aba no `App.jsx`
**What**: container com mês ("›" travado no atual), sub-abas, carregamento/erro/tentar de novo do grupo ativo. Aba só para admin depois de Financeiro. Exportar `DIAS`/`HORARIOS` do `Escala.jsx` se ainda não estiverem exportados.
**Where**: `frontend/src/components/Relatorios.jsx`, `frontend/src/App.jsx`
**Depends on**: T12–T15 · **Requirement**: REL-01, REL-02, REL-18
**Done when**: [ ] membro não vê a aba · [ ] troca de mês recarrega · [ ] Ocupação não mostra o seletor de mês · [ ] build e lint OK
**Tests**: none · **Gate**: build (npm)

### T17: Impressão por relatório
**What**: `CabecalhoImpressao`, botão "Imprimir / PDF" + dica "Salvar como PDF", bloco `@media print` (A4, sem menus, quebras, `print-color-adjust`).
**Where**: `frontend/src/components/relatorios/CabecalhoImpressao.jsx`, `Relatorios.jsx`, `App.css`
**Depends on**: T16 · **Requirement**: REL-16
**Done when**: [ ] PDF gerado pelo Chromium (`page.pdf` no Playwright) sem topbar e sem abas, com cabeçalho, sem colunas cortadas
**Tests**: none (verificação visual em T19) · **Gate**: build (npm)

### T18: Fechamento do mês (P2)
**What**: botão "Fechamento do mês", `allSettled` dos 4, capa, `.rel-secao` com quebra de página, print e desmontagem no `afterprint`. Aborta com aviso se algum grupo falhar.
**Where**: `frontend/src/components/Relatorios.jsx` (ou `relatorios/Fechamento.jsx`), `App.css`
**Depends on**: T17 · **Requirement**: REL-17
**Done when**: [ ] PDF com capa + 4 seções em páginas novas · [ ] falha simulada de um grupo dá aviso e não imprime · [ ] build e lint OK
**Tests**: none (verificação visual em T19) · **Gate**: build (npm)

### T19: Verificação visual (Playwright + API mockada)
**What**: prints desktop/celular dos 4 relatórios (com dados e vazios), PDF de um relatório e do fechamento, aba escondida para membro. Segue [[front-verify-mock-sandbox]].
**Where**: scratchpad (script descartável)
**Depends on**: T18 · **Requirement**: REL-01, REL-16, REL-17, REL-18
**Done when**: [ ] prints e PDFs conferidos · [ ] ajustes de layout aplicados
**Tests**: none · **Gate**: visual

### T20: Deploy + smoke + documentação
**What**: back pelo atalho sem Docker (changeset só `Modify ClinicaApiFunction`, **sem** `ClinicaTable` e sem Cognito), front com `deploy-front.ps1`, smoke (`/relatorios/*` sem token dá 401; com token admin real, medir o tempo do Atendimento, REL-19), atualizar STATE/ROADMAP/ARQUITETURA/TESTING.
**Depends on**: T19 · **Requirement**: REL-19 + entrega
**Done when**: [ ] no ar · [ ] Atendimento < 5 s · [ ] docs atualizados · [ ] commit
**Tests**: none · **Gate**: smoke

---

## Validação pré-aprovação

### Check 1: Granularidade
| Task | Entrega única? | OK |
|---|---|---|
| T1–T3 | 1 módulo/método cada | ✅ |
| T4–T7 | 1 grupo de funções cada (mesmo arquivo, por isso sequenciais) | ✅ |
| T8, T9 | schemas / router | ✅ |
| T10, T11 | api / gráficos | ✅ |
| T12–T15 | 1 componente cada | ✅ |
| T16–T18 | container / impressão / fechamento | ✅ |
| T19, T20 | verificação / entrega | ✅ |

### Check 2: Diagrama × Depends on
| Task | Depends on (definição) | No diagrama | OK |
|---|---|---|---|
| T1, T2, T3, T4 | None | Fase 1, sem setas de entrada | ✅ |
| T5 | T4 | T4 → T5 | ✅ |
| T6 | T5 | T5 → T6 | ✅ |
| T7 | T6 | T6 → T7 | ✅ |
| T8 | T7 | T7 → T8 (via "T1,T2,T3,T7 → T8") | ✅ |
| T9 | T1, T2, T3, T8 | T1, T2, T3 → (T8) → T9 | ✅ |
| T10 | T9 | T9 → T10 | ✅ |
| T11 | None | sem seta de entrada | ✅ |
| T12–T15 | T10, T11 | T10, T11 → T12–T15 | ✅ |
| T16 | T12–T15 | → T16 | ✅ |
| T17 | T16 | T16 → T17 | ✅ |
| T18 | T17 | T17 → T18 | ✅ |
| T19 | T18 | T18 → T19 | ✅ |
| T20 | T19 | T19 → T20 | ✅ |

### Check 3: Testes co-localizados (TESTING.md)
| Task | Camada | Exigido | Na task | OK |
|---|---|---|---|---|
| T1 | lógica de negócio + endpoint existente | unit | unit + suíte existente | ✅ |
| T2, T3 | repositório DynamoDB | unit (moto) + isolamento | unit (moto) + isolamento | ✅ |
| T4–T7 | lógica de negócio pura | unit | unit | ✅ |
| T8 | modelos Pydantic | unit | coberto via T9 | ✅ |
| T9 | endpoints + isolamento multi-tenant | unit (moto) | unit (moto) + isolamento + 403 | ✅ |
| T10–T18 | front | sem framework de teste no front (TESTING.md cobre só o back) | build + lint, visual em T19 | ✅ |
| T20 | infra/deploy | none | smoke | ✅ |

**Paralelismo**: unit (moto) é parallel-safe, então `[P]` em T1–T3 vale. T11–T15 são de front sem testes, então o `[P]` depende só do código.
