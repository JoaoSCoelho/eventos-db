# Banco de Dados de Eventos (EventOS / SBTC)

Repositório contendo o esquema relacional, script de geração de dados sintéticos e queries de inserção para o banco de dados de eventos (MATA60 - Banco de Dados / UFBA).

## Estrutura do Repositório

- `create-table.sql`: Script DDL em PostgreSQL com a criação de tabelas, tipos de dados, chaves primárias, estrangeiras e restrições de integridade.
- `gerar_dados.py`: Script Python que utiliza a biblioteca `Faker` para gerar dados sintéticos consistentes e com integridade referencial.
- `inserts_banco_de_dados.sql`: Script SQL gerado contendo todos os comandos `INSERT INTO` prontos para execução em lote no PostgreSQL.

## Pré-requisitos

- Python 3.10+
- Biblioteca `faker`:
  ```bash
  pip install faker
  ```

## Como Gerar Novos Dados

Para gerar um novo arquivo de inserts com parâmetros personalizados:

```bash
python gerar_dados.py --pessoas 60 --eventos 6 --inscricoes 100 --output inserts_banco_de_dados.sql
```

Parâmetros disponíveis:
- `--pessoas`: Quantidade de pessoas (padrão: 60)
- `--eventos`: Quantidade de eventos (padrão: 6)
- `--inscricoes`: Quantidade de inscrições (padrão: 100)
- `--output`: Nome do arquivo SQL de saída (padrão: `inserts_banco_de_dados.sql`)
- `--seed`: Seed aleatória para reproducibilidade (padrão: 42)

