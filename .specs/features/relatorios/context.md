# Relatórios: decisões do usuário (2026-11-09)

Decisões **travadas** (o Design e as Tasks não reabrem):

| # | Tema | Decisão | Consequência |
|---|------|---------|--------------|
| D1 | Grupos | **Os 4**: Financeiro, Alunos, Ocupação da escala, Atendimento | Todos são P1 |
| D2 | Formato | **Tela + PDF para imprimir** (Excel não foi escolhido) | Botão "Imprimir / PDF" em cada relatório |
| D3 | Quem vê | **Só admin**: a aba inteira | Router com `require_admin` no `APIRouter` (como o Financeiro). A aba fica escondida para membro |
| D4 | Período | **Mês + evolução de 12 meses** (sem intervalo livre) | Seletor de mês, padrão = mês corrente, sem futuro. Gráficos com os 12 meses que terminam no mês escolhido |
| D5 | Aula dada | **Só aulas registradas** (aba Pilates). A Agenda não conta | O relatório de Atendimento lê `SESSION#`, não `AGENDA#` |
| D6 | PDF | **Os dois**: PDF por relatório **e** fechamento do mês com os 4 grupos | O fechamento é P2 e reaproveita os componentes dos relatórios |

## Livre para o Design decidir (com recomendação inicial)

- **Gráficos sem biblioteca nova**: o front hoje só depende de React. Barras e linhas em SVG/CSS próprios mantêm o bundle leve e imprimem bem. Avaliar se uma lib leve compensa.
- **PDF via impressão do navegador** (`window.print()` + CSS `@media print`): sem lib de PDF e sem trabalho no back. O usuário escolhe "Salvar como PDF". Alternativa: gerar PDF no back, que é mais pesado e precisaria de dependência nova na Lambda (quebra o atalho de deploy sem Docker).
- **Atendimento em escala (REL-19)**: as aulas ficam sob a PK de cada aluno. Opções: (a) uma Query por aluno, em paralelo, no back; (b) GSI novo por clínica+data. Um GSI novo **altera a tabela de produção**, então a preferência é (a), medida contra o limite de 5 s.
- **Endpoints**: um por grupo (`GET /relatorios/financeiro?mes=`, `/alunos`, `/ocupacao`, `/atendimento`), cada um já agregado no back, para o front não somar milhares de itens.
