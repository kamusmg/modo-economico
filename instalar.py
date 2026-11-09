#!/usr/bin/env python3
"""Instala o modo econômico na ferramenta escolhida: python instalar.py <claude|opencode|codex>

Os papéis ficam em papeis/, os comandos em comandos/ e os modelos em modelos.ini.
Cada adaptador só traduz isso para o formato da ferramenta. Para somar outra ferramenta,
escreva uma função no molde de gerar_opencode e registre em ADAPTADORES.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence

RAIZ = Path(__file__).resolve().parent
# O Bloco de Notas pode salvar com BOM, e o BOM quebraria a leitura do cabeçalho.
ENCODING_DE_LEITURA = "utf-8-sig"


@dataclass(frozen=True)
class Documento:
    nome: str
    descricao: str
    so_leitura: bool
    corpo: str


Modelos = Mapping[str, str]
Arquivos = Dict[Path, str]
Gerador = Callable[[Sequence[Documento], Sequence[Documento], Modelos], Arquivos]


@dataclass(frozen=True)
class Adaptador:
    gerar: Gerador
    como_usar: str


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    ferramenta = ler_argumentos().ferramenta
    adaptador = ADAPTADORES[ferramenta]
    arquivos = adaptador.gerar(
        ler_documentos(RAIZ / "papeis"),
        ler_documentos(RAIZ / "comandos"),
        ler_modelos(RAIZ / "modelos.ini", ferramenta),
    )
    for destino, conteudo in arquivos.items():
        print(gravar(destino, conteudo))
    print(f"\nPronto. {adaptador.como_usar}")
    return 0


def ler_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Instala o modo econômico na ferramenta escolhida.")
    parser.add_argument("ferramenta", choices=sorted(ADAPTADORES))
    return parser.parse_args()


# --- Leitura ---------------------------------------------------------------------------------


def ler_documentos(pasta: Path) -> tuple[Documento, ...]:
    return tuple(ler_documento(arquivo) for arquivo in sorted(pasta.glob("*.md")))


def ler_documento(arquivo: Path) -> Documento:
    partes = arquivo.read_text(encoding=ENCODING_DE_LEITURA).split("---\n", 2)
    if len(partes) != 3 or partes[0].strip():
        raise SystemExit(f"{arquivo}: o arquivo precisa começar com um cabeçalho entre linhas ---")
    campos = ler_cabecalho(partes[1])
    if "descricao" not in campos:
        raise SystemExit(f"{arquivo}: falta o campo descricao no cabeçalho")
    return Documento(arquivo.stem, campos["descricao"], campos.get("so_leitura") == "sim", partes[2].strip())


def ler_cabecalho(texto: str) -> dict[str, str]:
    pares = (linha.split(":", 1) for linha in texto.splitlines() if ":" in linha)
    return {chave.strip(): valor.strip() for chave, valor in pares}


def ler_modelos(arquivo: Path, ferramenta: str) -> Modelos:
    config = configparser.ConfigParser(delimiters=("=",), interpolation=None)
    config.read(arquivo, encoding=ENCODING_DE_LEITURA)
    if ferramenta not in config:
        raise SystemExit(f"{arquivo.name} não tem a seção [{ferramenta}].")
    return dict(config[ferramenta])


def modelo_de(papel: Documento, modelos: Modelos) -> str:
    return modelos.get(papel.nome, "")


def esforco_de(papel: Documento, modelos: Modelos) -> str:
    return modelos.get(f"esforco_{papel.nome}", "")


# --- Adaptadores (funções puras: recebem os dados e devolvem destino -> conteúdo) ----------------


def gerar_claude(papeis: Sequence[Documento], comandos: Sequence[Documento], modelos: Modelos) -> Arquivos:
    pasta = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    agentes = {pasta / "agents" / f"{papel.nome}.md": agente_claude(papel, modelos) for papel in papeis}
    atalhos = {pasta / "commands" / f"{comando.nome}.md": comando_markdown(comando) for comando in comandos}
    return {**agentes, **atalhos}


def agente_claude(papel: Documento, modelos: Modelos) -> str:
    return markdown(
        {
            "name": papel.nome,
            "description": papel.descricao,
            "model": modelo_de(papel, modelos) or "inherit",
            "effort": esforco_de(papel, modelos),
            "tools": "Read, Grep, Glob, Bash" if papel.so_leitura else "",
        },
        papel.corpo,
    )


def gerar_opencode(papeis: Sequence[Documento], comandos: Sequence[Documento], modelos: Modelos) -> Arquivos:
    pasta = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "opencode"
    agentes = {pasta / "agents" / f"{papel.nome}.md": agente_opencode(papel, modelos) for papel in papeis}
    atalhos = {pasta / "commands" / f"{comando.nome}.md": comando_markdown(comando) for comando in comandos}
    return {**agentes, **atalhos}


def agente_opencode(papel: Documento, modelos: Modelos) -> str:
    # Testado nas versões 1.17 e 1.19: o formato "permissions:" dos docs novos é ignorado sem aviso.
    return markdown(
        {
            "description": papel.descricao,
            "mode": "subagent",
            "model": modelo_de(papel, modelos),
            "permission": {"edit": "deny"} if papel.so_leitura else {},
        },
        papel.corpo,
    )


def gerar_codex(papeis: Sequence[Documento], comandos: Sequence[Documento], modelos: Modelos) -> Arquivos:
    pasta = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    skills = Path.home() / ".agents" / "skills"
    agentes = {pasta / "agents" / f"{papel.nome}.toml": agente_codex(papel, modelos) for papel in papeis}
    atalhos = {
        skills / comando.nome / "SKILL.md": markdown({"name": comando.nome, "description": comando.descricao}, comando.corpo)
        for comando in comandos
    }
    return {**agentes, **atalhos}


def agente_codex(papel: Documento, modelos: Modelos) -> str:
    campos = {
        "name": papel.nome,
        "description": papel.descricao,
        "model": modelo_de(papel, modelos),
        "model_reasoning_effort": esforco_de(papel, modelos),
        "developer_instructions": papel.corpo,
    }
    # Toda string JSON também é string básica válida em TOML.
    return "".join(f"{chave} = {json.dumps(valor, ensure_ascii=False)}\n" for chave, valor in campos.items() if valor)


def comando_markdown(comando: Documento) -> str:
    return markdown({"description": comando.descricao}, comando.corpo)


def markdown(campos: Mapping[str, object], corpo: str) -> str:
    # JSON também é YAML válido: assim dois-pontos e aspas na descrição não quebram o cabeçalho.
    cabecalho = "\n".join(f"{chave}: {json.dumps(valor, ensure_ascii=False)}" for chave, valor in campos.items() if valor)
    return f"---\n{cabecalho}\n---\n\n{corpo}\n"


# --- Gravação ----------------------------------------------------------------------------------


def gravar(destino: Path, conteudo: str) -> str:
    if destino.exists() and destino.read_text(encoding=ENCODING_DE_LEITURA) == conteudo:
        return f"sem mudança  {destino}"
    copia = guardar_copia(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(conteudo)
    return f"instalado    {destino}" + (f"  (o anterior virou {copia.name})" if copia else "")


def guardar_copia(destino: Path) -> Optional[Path]:
    if not destino.exists():
        return None
    copia = destino.with_name(f"{destino.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
    destino.replace(copia)
    return copia


ADAPTADORES: Mapping[str, Adaptador] = {
    "claude": Adaptador(gerar_claude, "Abra o Claude Code e digite /economico (/normal desliga)."),
    "opencode": Adaptador(gerar_opencode, "Abra o OpenCode e digite /economico (/normal desliga)."),
    "codex": Adaptador(gerar_codex, "Abra o Codex e digite $economico ($normal desliga)."),
}

if __name__ == "__main__":
    sys.exit(main())
