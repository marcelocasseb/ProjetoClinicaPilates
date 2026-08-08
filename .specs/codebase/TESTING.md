# Testing

**Stack:** Python 3.13 (runtime Lambda) / 3.14 (local dev)
**Framework:** pytest
**AWS mocking:** moto — `moto[dynamodb,cognitoidp,s3]` (tudo em memória, sem tocar AWS real, sem Docker)
**Suíte atual:** **219 testes verdes** (`pytest -q`, ~3min)
**Coverage philosophy:** Pragmática — testar lógica de negócio, validações e acesso a dados (via mock). NÃO testar boilerplate de infraestrutura (template SAM, fiação de handler).

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Rationale |
| ---------- | ------------------ | --------- |
| Rotas/handlers FastAPI (endpoints) | unit | Lógica de request/response, status codes, validação |
| Camada de acesso a dados (repositório DynamoDB) | unit (com moto) | Persistência e queries por PK/SK |
| Modelos/validação (Pydantic) | unit | Regras de campo obrigatório, formatos |
| Handler Mangum (entrypoint Lambda) | unit | Adaptação evento API Gateway → app (smoke test) |
| Helpers de S3 (URLs pré-assinadas) | unit (com moto s3) | Validação de tipo, montagem de chave isolada, existência/remoção do objeto |
| **Isolamento multi-tenant** | unit, em TODA feature | Clínica A não pode ler/escrever dado de B — o teste mais importante do projeto |
| Template SAM / IaC | none | Boilerplate de infra; validado por `sam validate` + deploy manual |
| Configuração de projeto (scaffold, deps) | none | Sem lógica testável |

---

## Gate Check Commands

| Gate | Command | When |
| ---- | ------- | ---- |
| quick | `pytest -q` | Após tarefa com testes unit |
| full | `pytest -q` | Após integração de feature (idem quick por ora; evoluir com cobertura) |
| build | `python -m compileall src && pytest --collect-only -q` | Após tarefa de scaffold/infra sem testes próprios |

---

## Parallelism Assessment

| Test Type | Parallel-Safe | Rationale |
| --------- | ------------- | --------- |
| unit (moto) | Yes | moto isola estado em memória por teste; sem estado compartilhado |
| none (infra) | Yes | Sem execução de teste |

---

## Conventions

- Testes ficam em `tests/`, espelhando a estrutura de `src/`.
- Nome dos arquivos: `test_<modulo>.py`.
- Usar `@mock_aws` (moto) em fixtures que criam a tabela DynamoDB antes do teste.
- Fixtures compartilhadas em `tests/conftest.py`: `dynamo_table` (tabela + `TABLE_NAME`) e
  `imagens_ambiente` (bucket S3 + `IMAGES_BUCKET`, reaproveitando o mesmo `mock_aws` ativo —
  um único contexto mockado cobre DynamoDB **e** S3).
- Cada task que cria uma camada com test type != none escreve os testes na MESMA task.
- **Toda feature aninhada no paciente** testa também: `404` para paciente inexistente e
  isolamento entre clínicas (ver `test_imagens.py` como referência do padrão).
