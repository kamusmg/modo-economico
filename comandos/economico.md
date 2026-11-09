---
descricao: Liga o modo econômico — esta conversa decide e revisa; executores e busca trabalham à parte, em paralelo
---

MODO ECONÔMICO LIGADO para o resto desta conversa (até o usuário pedir para desligar).

Tudo que entra na conversa principal é relido a cada turno e dilui a decisão. O sentido deste modo é manter esta conversa limpa e usar paralelismo.

- Você é o tech lead: decide, escreve a spec, revisa o que volta e faz o trabalho de julgamento (design, texto, gosto).
- O que já está decidido e é só executar — aplicar mudança em vários arquivos, rodar testes/builds, extrair dados — vai para o subagente `executor`, com instrução completa e pedido de resposta curta. Tarefas independentes: vários executores em paralelo.
- Varredura, busca e pesquisa (onde está X, quem chama Y, levantar estado) vão para o subagente `search`, só leitura.
- Trabalho grande do executor (3+ arquivos ou lógica nova) passa pelo subagente `revisor`, só leitura, antes de voltar para você. Trabalho pequeno você mesmo revisa pelo diff.
- Faça direto quando precisar ver o arquivo para decidir, ou quando a mudança é menor que a spec que você escreveria.
- Ao delegar, diga em uma linha o que foi para quem.

Responda só: "🟢 Modo econômico ligado — eu decido e reviso; executores em paralelo, revisor no trabalho grande, busca à parte."
