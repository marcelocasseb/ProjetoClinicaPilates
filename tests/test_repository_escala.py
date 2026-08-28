"""Testes do repositório da Escala Semanal (ESC-01, 02, 04, 05, 08, 11)."""
import boto3
import pytest

from app.repository_escala import EscalaRepository

CLINIC = "clinica-zen"
OUTRA = "clinica-corpo"


@pytest.fixture
def repo(dynamo_table):
    return EscalaRepository(clinic_id=CLINIC, table_name=dynamo_table)


def _tabela(nome):
    return boto3.resource("dynamodb", region_name="us-east-1").Table(nome)


def test_create_persiste_na_chave_esperada(repo, dynamo_table):
    repo.create(1, "07:00", "p1", "Rebecca")
    item = _tabela(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINIC}", "SK": "ESCALA#1#07:00#p1"}
    )["Item"]
    assert item["clinicId"] == CLINIC
    assert int(item["dia"]) == 1
    assert item["hora"] == "07:00"
    assert item["pacienteId"] == "p1"
    assert item["pacienteNome"] == "Rebecca"
    assert item["criadoEm"]


def test_create_devolve_item_de_dominio_sem_chaves_internas(repo):
    criado = repo.create(1, "07:00", "p1", "Rebecca")
    assert criado["dia"] == 1
    assert "PK" not in criado and "SK" not in criado


def test_create_duplicado_devolve_none_e_nao_duplica(repo):
    assert repo.create(1, "07:00", "p1", "Rebecca") is not None
    assert repo.create(1, "07:00", "p1", "Rebecca") is None
    assert len(repo.list_all()) == 1


def test_mesmo_aluno_em_varios_horarios(repo):
    """O caso normal: seg e qua às 7h."""
    repo.create(1, "07:00", "p1", "Rebecca")
    repo.create(3, "07:00", "p1", "Rebecca")
    assert len(repo.list_all()) == 2


def test_varios_alunos_no_mesmo_horario(repo):
    repo.create(1, "07:00", "p1", "Rebecca")
    repo.create(1, "07:00", "p2", "Mariana")
    assert len(repo.list_all()) == 2


def test_list_ordena_por_dia_hora_nome(repo):
    repo.create(3, "07:00", "p3", "Carla")
    repo.create(1, "19:00", "p4", "Bruno")
    repo.create(1, "07:00", "p2", "Zeca")
    repo.create(1, "07:00", "p1", "Ana")
    ordem = [(m["dia"], m["hora"], m["pacienteNome"]) for m in repo.list_all()]
    assert ordem == [
        (1, "07:00", "Ana"),
        (1, "07:00", "Zeca"),
        (1, "19:00", "Bruno"),
        (3, "07:00", "Carla"),
    ]


def test_hora_com_zero_a_esquerda_ordena_cronologicamente(repo):
    """`07:00` antes de `19:00` — é o zero à esquerda que garante isso no SK."""
    repo.create(1, "19:00", "p1", "A")
    repo.create(1, "07:00", "p2", "B")
    assert [m["hora"] for m in repo.list_all()] == ["07:00", "19:00"]


def test_list_ignora_outros_itens_da_mesma_particao(repo, dynamo_table):
    """`METADATA` e `APARELHO#` moram na mesma PK e não podem vazar na grade."""
    tabela = _tabela(dynamo_table)
    tabela.put_item(Item={"PK": f"CLINIC#{CLINIC}", "SK": "METADATA", "nome": "Clínica Zen"})
    tabela.put_item(Item={"PK": f"CLINIC#{CLINIC}", "SK": "APARELHO#a1", "nome": "Reformer"})
    repo.create(1, "07:00", "p1", "Rebecca")
    itens = repo.list_all()
    assert len(itens) == 1
    assert itens[0]["pacienteId"] == "p1"


def test_list_vazia_quando_nao_ha_matricula(repo):
    assert repo.list_all() == []


def test_delete_remove_fisicamente(repo, dynamo_table):
    repo.create(1, "07:00", "p1", "Rebecca")
    assert repo.delete(1, "07:00", "p1") is True
    assert repo.list_all() == []
    resp = _tabela(dynamo_table).get_item(
        Key={"PK": f"CLINIC#{CLINIC}", "SK": "ESCALA#1#07:00#p1"}
    )
    assert "Item" not in resp  # remoção física, não soft delete


def test_delete_inexistente_devolve_false(repo):
    assert repo.delete(1, "07:00", "fantasma") is False


def test_delete_repetido_devolve_false(repo):
    repo.create(1, "07:00", "p1", "Rebecca")
    assert repo.delete(1, "07:00", "p1") is True
    assert repo.delete(1, "07:00", "p1") is False


def test_delete_nao_afeta_outros_horarios_do_aluno(repo):
    repo.create(1, "07:00", "p1", "Rebecca")
    repo.create(3, "07:00", "p1", "Rebecca")
    repo.delete(1, "07:00", "p1")
    restantes = repo.list_all()
    assert len(restantes) == 1
    assert restantes[0]["dia"] == 3


def test_recolocar_aluno_no_mesmo_horario_depois_de_remover(repo):
    """O que o soft delete quebraria: a chave precisa ficar livre de novo."""
    repo.create(1, "07:00", "p1", "Rebecca")
    repo.delete(1, "07:00", "p1")
    assert repo.create(1, "07:00", "p1", "Rebecca") is not None


# --- Isolamento multi-tenant (ESC-08) ---


def test_outra_clinica_nao_ve_a_escala(dynamo_table, repo):
    repo.create(1, "07:00", "p1", "Rebecca")
    outra = EscalaRepository(clinic_id=OUTRA, table_name=dynamo_table)
    assert outra.list_all() == []


def test_outra_clinica_nao_apaga_matricula(dynamo_table, repo):
    repo.create(1, "07:00", "p1", "Rebecca")
    outra = EscalaRepository(clinic_id=OUTRA, table_name=dynamo_table)
    assert outra.delete(1, "07:00", "p1") is False
    assert len(repo.list_all()) == 1


def test_mesma_chave_em_clinicas_diferentes_coexiste(dynamo_table, repo):
    outra = EscalaRepository(clinic_id=OUTRA, table_name=dynamo_table)
    assert repo.create(1, "07:00", "p1", "Rebecca") is not None
    assert outra.create(1, "07:00", "p1", "Rebecca") is not None
    assert len(repo.list_all()) == 1
    assert len(outra.list_all()) == 1


# --- Paginação (ESC-11) ---


class _TabelaPaginada:
    """Simula uma Query cortada em 2 páginas (o corte de 1 MB do DynamoDB)."""

    def __init__(self):
        self.chamadas = []

    def query(self, **kwargs):
        self.chamadas.append(kwargs)
        if "ExclusiveStartKey" not in kwargs:
            return {
                "Items": [{"PK": "x", "SK": "y", "dia": 1, "hora": "07:00", "pacienteNome": "Ana"}],
                "LastEvaluatedKey": {"PK": "x", "SK": "y"},
            }
        return {
            "Items": [{"PK": "x", "SK": "z", "dia": 2, "hora": "08:00", "pacienteNome": "Bruno"}]
        }


def test_list_all_segue_o_last_evaluated_key(repo):
    fake = _TabelaPaginada()
    repo._table = fake
    itens = repo.list_all()
    assert [m["pacienteNome"] for m in itens] == ["Ana", "Bruno"]
    assert len(fake.chamadas) == 2
    assert fake.chamadas[1]["ExclusiveStartKey"] == {"PK": "x", "SK": "y"}
