"""Padronização de textos digitados (nome, telefone, e-mail).

Cada pessoa digita do seu jeito ("MARIA DA SILVA", "maria  da silva", "91981111111"),
e sem padrão a lista fica bagunçada, a busca falha e a ordenação alfabética mente
(o DynamoDB ordena "Z" maiúsculo antes de "a" minúsculo). Os schemas aplicam estas
funções na entrada, então tudo é gravado já padronizado.
"""
import re
from typing import Optional

# Partículas do português que ficam minúsculas no meio do nome ("Maria da Silva").
_PARTICULAS = {"da", "das", "de", "do", "dos", "e"}
# Algarismos romanos de sufixo ("João II") ficam maiúsculos.
_ROMANOS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
# Sigla curta digitada em maiúsculas ("Maria MT", "Priscila G. M. Valente") fica.
# Só até 2 letras: com 3, nomes como "ANA" e "LUZ" passariam por sigla.
_SIGLA_MAX = 2


def _capitaliza(parte: str) -> str:
    return parte[:1].upper() + parte[1:].lower()


def _letras(palavra: str) -> str:
    return "".join(c for c in palavra if c.isalpha())


def _palavra(palavra: str, primeira: bool, tudo_maiusculo: bool) -> str:
    # Com algarismo é código, não nome ("BR-316", "12B", "SP-55"): fica como veio.
    if any(c.isdigit() for c in palavra):
        return palavra
    letras = _letras(palavra)
    baixa = palavra.lower()
    if not primeira and baixa in _PARTICULAS:
        return baixa
    if not primeira and baixa in _ROMANOS:
        return baixa.upper()
    # Maiúsculas e minúsculas misturadas = escrito assim de propósito ("Shangri-lá",
    # "McDonald", "d'Ávila"): respeita. Só arruma o que veio todo minúsculo ou todo
    # maiúsculo — que é o caso de quem digitou sem cuidar.
    if letras and not letras.islower() and not letras.isupper():
        return palavra
    # Sigla curta em maiúsculas no meio de um nome normal fica ("Maria MT").
    if letras.isupper() and len(letras) <= _SIGLA_MAX and not tudo_maiusculo and not primeira:
        return palavra
    # Hífen e apóstrofo: cada pedaço com inicial maiúscula ("Ana-Clara", "D'Ávila").
    return re.sub(r"[^\-'’]+", lambda m: _capitaliza(m.group(0)), palavra)


def nome_proprio(nome: Optional[str]) -> Optional[str]:
    """`"  MARIA  DA silva "` → `"Maria da Silva"`. Vazio/None passa direto."""
    if not isinstance(nome, str):
        return nome
    palavras = nome.split()
    letras = _letras(nome)
    tudo_maiusculo = bool(letras) and letras.isupper()
    return " ".join(_palavra(p, i == 0, tudo_maiusculo) for i, p in enumerate(palavras))


def espacos(texto: Optional[str]) -> Optional[str]:
    """Só junta espaços repetidos e tira os das pontas (complemento: "AP 12B")."""
    if not isinstance(texto, str):
        return texto
    return " ".join(texto.split())


def telefone(tel: Optional[str]) -> Optional[str]:
    """Telefone brasileiro → `(91) 98111-1111` / `(91) 3222-1111`.

    Aceita com ou sem máscara e com `+55`. Fora desse formato (internacional, ramal…)
    devolve o texto só sem os espaços das pontas — melhor guardar como veio do que
    descartar um número válido de outro país.
    """
    if not isinstance(tel, str):
        return tel
    limpo = tel.strip()
    # "+" com outro código de país (ex.: +1 415…): não é número brasileiro, mesmo
    # que por acaso tenha 10 ou 11 dígitos.
    if limpo.startswith("+") and not re.sub(r"[^\d+]", "", limpo).startswith("+55"):
        return limpo
    d = re.sub(r"\D", "", limpo)
    if len(d) in (12, 13) and d.startswith("55"):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return limpo


def email(valor: Optional[str]) -> Optional[str]:
    """E-mail sem espaços e em minúsculas (e-mail não diferencia maiúsculas)."""
    if not isinstance(valor, str):
        return valor
    return valor.strip().lower()
