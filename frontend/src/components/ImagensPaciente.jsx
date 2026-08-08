import { useEffect, useRef, useState } from "react";
import { imagensApi, uploadParaS3 } from "../api";

const LIMITE = 5;
const TIPOS_OK = ["image/jpeg", "image/png", "image/webp"];
const TAMANHO_MAX = 5 * 1024 * 1024; // 5 MB

// Painel de imagens do paciente (até 5, no nível do paciente — não por consulta).
// Upload em 2 fases: pede a URL pré-assinada, envia direto ao S3, confirma.
export default function ImagensPaciente({ pacienteId }) {
  const [imagens, setImagens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const inputRef = useRef(null);

  async function carregar() {
    setErro("");
    setLoading(true);
    try {
      setImagens(await imagensApi.list(pacienteId));
    } catch (e) {
      setErro(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pacienteId]);

  async function onArquivo(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // permite reescolher o mesmo arquivo depois
    if (!file) return;

    if (!TIPOS_OK.includes(file.type)) {
      setErro("Formato não aceito. Envie uma imagem JPEG, PNG ou WEBP.");
      return;
    }
    if (file.size > TAMANHO_MAX) {
      setErro("Imagem muito grande. O limite é 5 MB.");
      return;
    }

    setErro("");
    setEnviando(true);
    try {
      const { id, uploadUrl } = await imagensApi.solicitarUpload(pacienteId, file.type);
      await uploadParaS3(uploadUrl, file);
      await imagensApi.confirmar(pacienteId, id, file.type);
      await carregar();
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  async function remover(img) {
    if (!confirm("Remover esta imagem?")) return;
    setErro("");
    try {
      await imagensApi.remove(pacienteId, img.id);
      await carregar();
    } catch (e) {
      setErro(e.message);
    }
  }

  const cheio = imagens.length >= LIMITE;

  return (
    <div className="card">
      <div className="img-header">
        <h2>Imagens do paciente ({imagens.length}/{LIMITE})</h2>
        <button
          type="button"
          className="btn primary"
          disabled={enviando || cheio}
          onClick={() => inputRef.current?.click()}
        >
          {enviando ? "Enviando..." : "+ Adicionar imagem"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          style={{ display: "none" }}
          onChange={onArquivo}
        />
      </div>

      {erro && <div className="erro">{erro}</div>}
      {cheio && <p className="muted">Limite de {LIMITE} imagens atingido. Remova uma para adicionar outra.</p>}

      {loading ? (
        <div className="loading">
          <span className="spinner" />
          Carregando imagens…
        </div>
      ) : imagens.length === 0 ? (
        <p className="muted">Nenhuma imagem anexada a este paciente.</p>
      ) : (
        <div className="img-grid">
          {imagens.map((img) => (
            <div key={img.id} className="img-thumb">
              <a href={img.url} target="_blank" rel="noopener noreferrer" title="Abrir em tamanho real">
                <img src={img.url} alt="Imagem do paciente" loading="lazy" />
              </a>
              <button type="button" className="img-remove" onClick={() => remover(img)} title="Remover">
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
