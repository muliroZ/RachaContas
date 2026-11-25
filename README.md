# RachaContas
Projeto da disciplina de Padrões de Projeto da Universidade de Pernambuco (UPE)

**Equipe:** Murilo Andrade, Maria Carolina, José Severo e Gustavo Vilela

## Visão geral

Um grupo (viagem, república, rolê) registra gastos e o sistema calcula quem deve a quem, com o menor número possível de transferências. 

**Stack:** 
- **Python**
- **Flask** 
- **SQLite** 
- **SQLAlchemy**
- **Alembic**
- **Pydantic**
- **React + TypeScript**

## Padrões Implementados

O projeto implementa 8 padrões GoF, cobrindo as três categorias:

**Criacionais:** Factory Method<br>
**Estruturais:** Adapter, Composite, Decorator e Facade<br>
**Comportamentais:** Command, Observer e Strategy<br>

## Modelo de dados

Oito tabelas, todas versionadas com Alembic. Valores monetários em centavos (inteiro), para evitar conversões erradas do float.

| Tabela | Campos principais | Usada por |
| --- | --- | --- |
| `grupo` | nome, criado_em, limite_alerta (opcional, centavos) | todos; Observer |
| `participante` | nome, grupo_id | todos |
| `despesa` | grupo_id, pagador_id, descricao, tipo_divisao, params_divisao (JSON), excluida | Strategy, Factory Method, Command |
| `item` | despesa_id, parent_id (auto-relacionamento), nome, valor | Composite |
| `item_consumidor` | item_id, participante_id (chave composta) | Strategy (divisão por consumo) |
| `ajuste` | despesa_id, tipo (taxa_servico, couvert, gorjeta, desconto), valor, ordem | Decorator |
| `historico_comando` | grupo_id, tipo, estado_antes (JSON), estado_depois (JSON), desfeito, criado_em | Command |
| `notificacao` | participante_id, mensagem, lida, criado_em | Observer |

**Relacionamentos:**

```
grupo 1 ── N participante
grupo 1 ── N despesa
grupo 1 ── N historico_comando
participante 1 ── N despesa        (pagador_id)
participante 1 ── N notificacao
despesa 1 ── N item               (cascata)
despesa 1 ── N ajuste             (cascata)
item 1 ── N item                  (parent_id, o Composite)
item N ── N participante          (via item_consumidor)
```

## Como rodar o projeto

**Dependências:**

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (gerenciador de pacotes)

---

Para rodar o projeto (até o atual momento), siga estes passos:

```bash
git clone https://github.com/muliroZ/RachaContas.git
cd RachaContas/
uv sync --frozen
alembic upgrade head
uv run rachacontas
```

Com isso, você irá sincronizar as dependências do projeto, criar as tabelas no banco (`contas.db`) e inicializar o servidor de desenvolvimento Flask em `http://127.0.0.1:5000/`. 

> Até o momento ainda não há nenhum endpoint/funcionalidade implementada.

## Licença

Este projeto está sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais informações.

## Créditos

- Murilo Andrade [muliroZ](https://github.com/muliroZ)
- Maria Carolina [CarolinaaCabral](https://github.com/CarolinaaCabral)
- José Severo [Severoabreu](https://github.com/Severoabreu)
- Gustavo Vilela [Gustavo0606](https://github.com/Gustavo0606)

> _Feito com amor e Python_
