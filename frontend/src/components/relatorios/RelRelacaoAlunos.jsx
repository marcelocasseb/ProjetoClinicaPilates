import { formatDataBR, maskTelefone } from "../../utils/format";
import { plural, reais } from "./formato";

function textoPlano(a) {
  if (!a.plano) return "Sem plano";
  if (a.isento) return "Isento";
  const partes = [`${reais(a.plano.valorCentavos)}/mês`];
  if (a.plano.frequencia) partes.push(`${a.plano.frequencia}x/sem`);
  if (a.plano.diaVencimento) partes.push(`vence dia ${a.plano.diaVencimento}`);
  return partes.join(" · ");
}

// Relação de alunos ativos (REL-21): retrato de hoje, sem mês.
export default function RelRelacaoAlunos({ dados }) {
  return (
    <div className="rel-relatorio">
      <p className="rel-nota no-print">Retrato de hoje: lista todos os alunos ativos, sem depender do mês escolhido.</p>
      {dados.alunos.length === 0 ? (
        <p className="muted rel-vazio">Nenhum aluno ativo.</p>
      ) : (
        <table className="rel-tabela rel-relacao">
          <thead>
            <tr>
              <th>Nome</th>
              <th>Telefone</th>
              <th>E-mail</th>
              <th>Nascimento</th>
              <th>Plano</th>
              <th>Horários</th>
            </tr>
          </thead>
          <tbody>
            {dados.alunos.map((a) => (
              <tr key={a.id}>
                <td>{a.nome}</td>
                <td className="nowrap">{a.telefone ? maskTelefone(a.telefone) : "—"}</td>
                <td className="quebra">{a.email || "—"}</td>
                <td className="nowrap">{a.dataNascimento ? formatDataBR(a.dataNascimento) : "—"}</td>
                <td>{textoPlano(a)}</td>
                <td>{a.horarios.length ? a.horarios.join(", ") : "—"}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={6}>Total: {plural(dados.total, "aluno ativo", "alunos ativos")}</td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  );
}
