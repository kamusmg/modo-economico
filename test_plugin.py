"""Testes do plugin do Claude Code. Rode com: python -m unittest"""
import json
import unittest

import instalar

RAIZ = instalar.RAIZ
PLUGIN = RAIZ / "plugin"
# O plugin é em inglês e os papéis em português: sem este mapa, um papel novo ficaria de fora sem aviso.
PAPEL_DO_AGENTE = {"executor": "executor", "reviewer": "revisor", "search": "search"}
NOME_DO_PLUGIN = "modo-economico"


def ler_agente(nome: str) -> dict[str, str]:
    partes = (PLUGIN / "agents" / f"{nome}.md").read_text(encoding="utf-8").split("---\n", 2)
    return {chave: valor.strip('"') for chave, valor in instalar.ler_cabecalho(partes[1]).items()}


class TestPlugin(unittest.TestCase):
    def test_marketplace_aponta_para_a_pasta_do_plugin(self):
        marketplace = json.loads((RAIZ / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        entrada = marketplace["plugins"][0]
        self.assertEqual(entrada["name"], NOME_DO_PLUGIN)
        self.assertTrue((RAIZ / entrada["source"] / ".claude-plugin" / "plugin.json").is_file())

    def test_todo_papel_tem_agente_no_plugin(self):
        papeis = {documento.nome for documento in instalar.ler_documentos(RAIZ / "papeis")}
        agentes = {arquivo.stem for arquivo in (PLUGIN / "agents").glob("*.md")}
        self.assertEqual(papeis, set(PAPEL_DO_AGENTE.values()))
        self.assertEqual(agentes, set(PAPEL_DO_AGENTE))

    def test_so_leitura_fica_igual_ao_papel(self):
        papeis = {documento.nome: documento for documento in instalar.ler_documentos(RAIZ / "papeis")}
        for agente, papel in PAPEL_DO_AGENTE.items():
            ferramentas = ler_agente(agente).get("tools", "")
            esperado = "Read, Grep, Glob, Bash" if papeis[papel].so_leitura else ""
            self.assertEqual(ferramentas, esperado, agente)

    def test_nome_do_agente_bate_com_o_arquivo(self):
        for agente in PAPEL_DO_AGENTE:
            self.assertEqual(ler_agente(agente)["name"], agente)

    def test_comando_on_cita_cada_agente_com_o_prefixo_do_plugin(self):
        texto = (PLUGIN / "commands" / "on.md").read_text(encoding="utf-8")
        for agente in PAPEL_DO_AGENTE:
            self.assertIn(f"`{NOME_DO_PLUGIN}:{agente}`", texto)


if __name__ == "__main__":
    unittest.main()
