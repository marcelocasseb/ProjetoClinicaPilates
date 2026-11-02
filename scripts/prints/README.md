# Prints do site

Gera as imagens do sistema usadas no site informativo ([site/](../../site/)), com um estúdio
fictício ("Studio Equilíbrio Pilates"). Nada toca a AWS: o backend é o
[dev_local.py](../dev_local.py) (DynamoDB e S3 simulados) com mais dados de exemplo.

## Como rodar

Três terminais, na raiz do projeto:

```powershell
# 1. Backend local com os dados da vitrine (porta 8000)
.venv\Scripts\python scripts\prints\dev_vitrine.py

# 2. Front local com upload de imagens simulado (porta 5173)
cd frontend; $env:VITE_MOCK_IMAGENS = "1"; npm run dev:local

# 3. Prints (a 1ª vez: npm install)
cd scripts\prints; npm install
node telas.js        # Início, Pacientes, Agenda, Escala, Financeiro... (computador e celular)
node posturas.js     # 4 fotos ilustrativas de postura (silhuetas)
node aula_fotos.js   # aula de Pilates sendo registrada + fotos na ficha do aluno
```

As imagens saem em `scripts/prints/out/` (fora do git). O login é simulado com um token falso
no navegador, e o relógio do navegador é fixado na próxima segunda-feira às 08:15, para a tela
inicial aparecer com aula em andamento.

O Chromium usado é o que já está em `%LOCALAPPDATA%\ms-playwright\chromium-1234`. Se mudar de
máquina, ajuste o caminho `CHROME` nos scripts (ou rode `npx playwright install chromium`).

## Quais arquivos vão para o site

Copie de `out/` para `site/img/`:

| Gerado em `out/` | Nome em `site/img/` |
|---|---|
| `desk-inicio.jpg`, `desk-agenda.jpg`, `desk-escala.jpg`, `desk-financeiro.jpg`, `desk-pacientes.jpg` | mesmo nome |
| `desk-aula.jpg`, `desk-fotos.jpg` | mesmo nome |
| `mob-inicio.jpg`, `mob-escala.jpg` | mesmo nome |
| `posturas/1-jan-lateral.jpg` … `posturas/4-abr-frente.jpg` | `foto-1.jpg` … `foto-4.jpg` |

O `logo.jpg` do site é o [pilatesone-icon.jpg](../../frontend/src/assets/pilatesone-icon.jpg) do front.
