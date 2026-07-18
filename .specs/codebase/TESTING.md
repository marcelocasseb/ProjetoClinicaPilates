# Testing

**Stack:** Python 3.13 (runtime Lambda) / 3.14 (local dev)
**Framework:** pytest
**AWS mocking:** moto (mock do DynamoDB em memória — sem tocar AWS real, sem Docker)
**Coverage philosophy:** Pragmática — testar lógica de negócio, validações e acesso a dados (via mock). NÃO testar boilerplate de infraestrutura (template SAM, fiação de handler).

---

## Test Coverage Matrix

| Code Layer | Required Test Type | Rationale |
| ---------- | ------------------ | --------- |
| Rotas/handlers FastAPI (endpoints) | unit | Lógica de request/response, status codes, validação |
| Camada de acesso a dados (repositório DynamoDB) | unit (com moto) | Persistência e queries por PK/SK |
| Modelos/validação (Pydantic) | unit | Regras de campo obrigatório, formatos |
| Handler Mangum (entrypoint Lambda) | unit | Adaptação evento API Gateway → app (smoke test) |
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
- Cada task que cria uma camada com test type != none escreve os testes na MESMA task.
