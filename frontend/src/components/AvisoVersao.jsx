import { useEffect, useState } from "react";

// Aviso de versão nova. A aba pode ficar aberta por dias sem recarregar — e o
// re-login pelo modal de sessão NÃO recarrega a página (de propósito, para não
// perder formulário). Então a aba consulta /version.json de tempos em tempos e,
// se a versão publicada for outra, mostra uma faixa com "Atualizar". Não
// recarregamos sozinhos: o usuário clica quando terminar o que está fazendo.
const INTERVALO_MS = 5 * 60_000;

async function versaoPublicada() {
  try {
    const res = await fetch(`/version.json?t=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) return null;
    const dados = await res.json();
    return dados?.version || null;
  } catch {
    return null; // offline / falha de rede: tenta na próxima
  }
}

export default function AvisoVersao() {
  const [temNova, setTemNova] = useState(false);

  useEffect(() => {
    if (import.meta.env.DEV) return; // `npm run dev` não publica version.json

    let ativo = true;
    async function checar() {
      const publicada = await versaoPublicada();
      if (ativo && publicada && publicada !== __APP_VERSION__) setTemNova(true);
    }

    // Checa ao voltar para a aba (caso comum: PC ficou parado) e periodicamente.
    function aoVoltar() {
      if (document.visibilityState === "visible") checar();
    }
    const timer = setInterval(checar, INTERVALO_MS);
    document.addEventListener("visibilitychange", aoVoltar);
    checar();
    return () => {
      ativo = false;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", aoVoltar);
    };
  }, []);

  if (!temNova) return null;

  return (
    <div className="aviso-versao" role="status">
      <span>Nova versão do sistema disponível.</span>
      <button type="button" className="btn primary" onClick={() => window.location.reload()}>
        Atualizar
      </button>
    </div>
  );
}
