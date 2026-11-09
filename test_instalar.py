"""Testes dos adaptadores. Rode com: python -m unittest"""
import configparser
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import instalar

EXECUTOR = instalar.Documento("executor", "Faz o trabalho", False, "Você executa.")
SEARCH = instalar.Documento("search", 'Busca: acha "X"', True, "Você busca.")
COMANDO = instalar.Documento("economico", "Liga o modo", False, "Modo ligado.")


class ComPastaIsolada(unittest.TestCase):
    def setUp(self):
        temporaria = tempfile.TemporaryDirectory()
        self.addCleanup(temporaria.cleanup)
        self.home = Path(temporaria.name)
        ambiente = {
            "CLAUDE_CONFIG_DIR": str(self.home / ".claude"),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "CODEX_HOME": str(self.home / ".codex"),
        }
        for patcher in (mock.patch.dict(os.environ, ambiente), mock.patch.object(Path, "home", return_value=self.home)):
            patcher.start()
            self.addCleanup(patcher.stop)


class TestAdaptadores(ComPastaIsolada):
    def test_claude_usa_modelo_e_esforco_do_ini(self):
        texto = instalar.agente_claude(EXECUTOR, {"executor": "opus", "esforco_executor": "max"})
        self.assertIn('model: "opus"', texto)
        self.assertIn('effort: "max"', texto)

    def test_claude_sem_modelo_herda_e_omite_esforco(self):
        texto = instalar.agente_claude(EXECUTOR, {"executor": ""})
        self.assertIn('model: "inherit"', texto)
        self.assertNotIn("effort", texto)

    def test_claude_so_leitura_fica_sem_ferramenta_de_edicao(self):
        self.assertIn('tools: "Read, Grep, Glob, Bash"', instalar.agente_claude(SEARCH, {}))
        self.assertNotIn("tools", instalar.agente_claude(EXECUTOR, {}))

    def test_descricao_com_dois_pontos_e_aspas_sai_entre_aspas(self):
        self.assertIn('description: "Busca: acha \\"X\\""', instalar.agente_claude(SEARCH, {}))

    def test_opencode_so_leitura_nega_edicao(self):
        self.assertIn('permission: {"edit": "deny"}', instalar.agente_opencode(SEARCH, {}))
        self.assertNotIn("permission", instalar.agente_opencode(EXECUTOR, {}))

    def test_opencode_sem_modelo_omite_o_campo(self):
        self.assertNotIn("model:", instalar.agente_opencode(EXECUTOR, {"executor": ""}))

    def test_opencode_mantem_provedor_e_variante(self):
        modelo = "anthropic/claude-sonnet-5-5#high"
        self.assertIn(f'model: "{modelo}"', instalar.agente_opencode(EXECUTOR, {"executor": modelo}))

    def test_codex_gera_toml_com_os_campos_obrigatorios(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest("tomllib só existe a partir do Python 3.11")
        dados = tomllib.loads(instalar.agente_codex(SEARCH, {"search": "m", "esforco_search": "low"}))
        self.assertEqual(dados["name"], "search")
        self.assertEqual(dados["description"], SEARCH.descricao)
        self.assertEqual(dados["model"], "m")
        self.assertEqual(dados["model_reasoning_effort"], "low")
        self.assertEqual(dados["developer_instructions"], SEARCH.corpo)

    def test_cada_ferramenta_grava_no_lugar_dela(self):
        esperados = {
            "claude": {".claude/agents/search.md", ".claude/commands/economico.md"},
            "opencode": {".config/opencode/agents/search.md", ".config/opencode/commands/economico.md"},
            "codex": {".codex/agents/search.toml", ".agents/skills/economico/SKILL.md"},
        }
        for ferramenta, caminhos in esperados.items():
            arquivos = instalar.ADAPTADORES[ferramenta].gerar((SEARCH,), (COMANDO,), {})
            gerados = {destino.relative_to(self.home).as_posix() for destino in arquivos}
            self.assertEqual(gerados, caminhos)


class TestGravacao(ComPastaIsolada):
    def test_guarda_copia_quando_o_arquivo_e_diferente(self):
        destino = self.home / "agents" / "executor.md"
        destino.parent.mkdir()
        destino.write_text("meu agente", encoding="utf-8")
        instalar.gravar(destino, "novo")
        copias = list(destino.parent.glob("executor.md.bak-*"))
        self.assertEqual(destino.read_text(encoding="utf-8"), "novo")
        self.assertEqual([copia.read_text(encoding="utf-8") for copia in copias], ["meu agente"])

    def test_nao_mexe_quando_o_conteudo_e_igual(self):
        destino = self.home / "executor.md"
        instalar.gravar(destino, "igual")
        self.assertIn("sem mudança", instalar.gravar(destino, "igual"))
        self.assertEqual(list(self.home.glob("*.bak-*")), [])


class TestLeitura(ComPastaIsolada):
    def test_aceita_arquivo_salvo_com_bom(self):
        arquivo = self.home / "papel.md"
        arquivo.write_bytes("﻿---\ndescricao: Teste\nso_leitura: sim\n---\n\nCorpo\n".encode("utf-8"))
        self.assertEqual(instalar.ler_documento(arquivo), instalar.Documento("papel", "Teste", True, "Corpo"))

    def test_cabecalho_faltando_explica_o_erro(self):
        arquivo = self.home / "papel.md"
        arquivo.write_text("só o corpo", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "cabeçalho"):
            instalar.ler_documento(arquivo)

    def test_secao_faltando_explica_o_erro(self):
        arquivo = self.home / "modelos.ini"
        arquivo.write_text("[claude]\nexecutor = opus\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "codex"):
            instalar.ler_modelos(arquivo, "codex")

    def test_todo_papel_tem_modelo_em_toda_ferramenta(self):
        config = configparser.ConfigParser(delimiters=("=",), interpolation=None)
        config.read(instalar.RAIZ / "modelos.ini", encoding="utf-8")
        papeis = instalar.ler_documentos(instalar.RAIZ / "papeis")
        self.assertEqual(sorted(config.sections()), sorted(instalar.ADAPTADORES))
        for ferramenta in config.sections():
            for papel in papeis:
                self.assertIn(papel.nome, config[ferramenta], f"[{ferramenta}] sem linha para {papel.nome}")


if __name__ == "__main__":
    unittest.main()
