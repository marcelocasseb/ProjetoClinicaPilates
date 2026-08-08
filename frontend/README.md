# Frontend — Pilates One

SPA em **React + Vite** do sistema de gestão da clínica. No ar em
**https://pilatesone.com.br** (S3 privado + CloudFront, stack `clinica-pilates-frontend`).

## Rodar local

```bash
npm install
npm run dev      # http://localhost:5173
```

O dev aponta para a **API real** (default em `src/config.js`) — não há backend local.
Faça login com um usuário Cognito de verdade.

## Variáveis de ambiente

| Variável | Onde | Para quê |
| --- | --- | --- |
| `VITE_API_URL` | opcional | Sobrescreve a URL da API (default: a stack no ar) |
| `VITE_COGNITO_CLIENT_ID` | `.env` | App Client do Cognito — **sem ele o login não funciona** |
| `VITE_COGNITO_REGION` | `.env` | Região do User Pool (default `us-east-1`) |
| `VITE_MOCK_IMAGENS` | `.env.development.local` | `1` = painel de imagens com mock in-memory (valida o front sem backend/S3). `0` = S3 real |

`.env` é versionado (só config pública de build). `.env*.local` **não** é — e só o
`npm run dev` os carrega, nunca o `npm run build`.

## Estrutura

| Arquivo | Papel |
| --- | --- |
| `src/App.jsx` | Layout, abas (Pacientes / Aparelhos / Pilates), sessão e logout |
| `src/api.js` | Cliente da API (envia `Authorization: Bearer`) + upload pro S3 |
| `src/auth.js` | Cognito: login, troca de senha no 1º acesso, tokens |
| `src/config.js` | URL da API e config do Cognito |
| `src/components/Pacientes.jsx` | Lista e ficha do paciente |
| `src/components/Avaliacoes.jsx` | Ficha clínica datada (aceita um `rodape` injetável) |
| `src/components/ImagensPaciente.jsx` | Painel de imagens (até 5, upload direto no S3) |
| `src/components/Pilates.jsx` | Registro de sessões/aulas |
| `src/components/Aparelhos.jsx` | Catálogo de aparelhos da clínica |
| `src/components/AdicionarMembro.jsx` | Admin cria membro da equipe |

## Publicar

```bash
npm run build
aws s3 sync dist s3://clinica-pilates-frontend-sitebucket-n6oomystbesc --delete
aws cloudfront create-invalidation --distribution-id EGYNGZONKGVLT --paths "/*"
```

Publicar o site **não** precisa de Docker nem SAM. Detalhes e verificação pós-deploy
em [`.specs/codebase/ARQUITETURA.md`](../.specs/codebase/ARQUITETURA.md).
