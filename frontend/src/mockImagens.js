// Mock in-memory do fluxo de imagens — SÓ para validar o front sem backend/S3.
// Ativado por VITE_MOCK_IMAGENS=1 (ver api.js). Nunca entra em produção.
//
// Reproduz o fluxo de 2 fases da API real:
//   solicitarUpload -> uploadParaS3(uploadUrl, file) -> confirmar
// e usa URL.createObjectURL(file) para mostrar a imagem de verdade que você escolher.

const _porPaciente = new Map(); // pacienteId -> [{id, url, contentType, criadoEm}]
const _pendentes = new Map(); // id -> objectURL do arquivo enviado

function _lista(pacienteId) {
  if (!_porPaciente.has(pacienteId)) _porPaciente.set(pacienteId, []);
  return _porPaciente.get(pacienteId);
}

const _delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));

export const imagensApiMock = {
  async list(pacienteId) {
    await _delay();
    return [..._lista(pacienteId)];
  },
  async solicitarUpload(pacienteId, contentType) {
    await _delay(150);
    if (_lista(pacienteId).length >= 5) {
      throw new Error("Limite de 5 imagens por paciente atingido");
    }
    const id = `mock-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    return { id, uploadUrl: id }; // uploadUrl carrega o id para o mock casar o arquivo
  },
  async confirmar(pacienteId, imagemId, contentType) {
    await _delay(200);
    const url = _pendentes.get(imagemId) || "";
    _pendentes.delete(imagemId);
    const meta = { id: imagemId, url, contentType, criadoEm: new Date().toISOString() };
    _lista(pacienteId).push(meta);
    return meta;
  },
  async remove(pacienteId, imagemId) {
    await _delay(150);
    _porPaciente.set(pacienteId, _lista(pacienteId).filter((i) => i.id !== imagemId));
    return null;
  },
};

// "Sobe" o arquivo: só guarda um object URL local para o preview real.
export async function uploadParaS3Mock(uploadUrl, file) {
  await _delay(200);
  _pendentes.set(uploadUrl, URL.createObjectURL(file));
}
