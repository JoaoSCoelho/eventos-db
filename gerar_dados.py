"""
Script para geração de dados sintéticos para o banco de dados (EventOS / SBTC).
Utiliza a biblioteca Faker para popular as tabelas definidas em create-table.txt.

Gera comandos INSERT INTO em conformidade com PostgreSQL, garantindo integridade
referencial, regras de negócio e restrições de unicidade.
"""

import argparse
import calendar
import datetime
import random
import sys
from decimal import Decimal

try:
    from faker import Faker
except ImportError:
    print("[ERRO] A biblioteca Faker não foi encontrada.")
    print("Instale-a executando no seu terminal: pip install faker")
    sys.exit(1)


def sql_val(val) -> str:
    """Formata valores de Python para representação SQL segura."""
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, Decimal)):
        return str(val)
    if isinstance(val, float):
        return f"{val:.2f}"
    if isinstance(val, datetime.datetime):
        return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
    if isinstance(val, datetime.date):
        return f"'{val.strftime('%Y-%m-%d')}'"
    # Strings: escapa apóstrofos simples duplicando-os (' -> '')
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def gerar_sql(
    num_pessoas: int = 600,
    num_eventos: int = 20,
    num_inscricoes: int = 1000,
    output_file: str = "inserts_banco_de_dados.sql",
    seed: int | None = 1,
):
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake_br = Faker("pt_BR")

    sql_statements = []

    def add_section_header(title: str):
        sql_statements.append(f"\n-- {'=' * 60}")
        sql_statements.append(f"-- {title}")
        sql_statements.append(f"-- {'=' * 60}\n")

    sql_statements.append("-- Script de inserção de dados sintéticos gerado automaticamente")
    sql_statements.append("-- Compatível com PostgreSQL")
    sql_statements.append("BEGIN;\n")

    # ==========================================================
    # 1. PESSOA
    # ==========================================================
    add_section_header("1. TABELA Pessoa")
    pessoas = []
    emails_usados = set()
    cpfs_usados = set()
    passaportes_usados = set()

    for p_id in range(1, num_pessoas + 1):
        # ~85% brasileiros com CPF e UF, ~15% estrangeiros com passaporte
        is_brasileiro = random.random() < 0.85
        nome = fake_br.name()

        # E-mail único
        base_email = fake_br.user_name()
        email = f"{base_email}{p_id}@example.com"
        while email in emails_usados:
            email = f"{fake_br.user_name()}{random.randint(100, 9999)}@example.com"
        emails_usados.add(email)

        dt_nascimento = fake_br.date_of_birth(minimum_age=18, maximum_age=72)

        if is_brasileiro:
            pais = "BRA"
            uf = fake_br.state_abbr()
            cpf_raw = fake_br.cpf().replace(".", "").replace("-", "")
            while cpf_raw in cpfs_usados:
                cpf_raw = fake_br.cpf().replace(".", "").replace("-", "")
            cpfs_usados.add(cpf_raw)
            cpf = cpf_raw
            passaporte = None
        else:
            pais = random.choice(["USA", "ARG", "PRT", "DEU", "FRA", "GBR", "CAN", "ESP", "ITA", "CHL"])
            uf = "EX"  # Exterior
            cpf = None
            pass_raw = fake_br.bothify(text="??#######").upper()
            while pass_raw in passaportes_usados:
                pass_raw = fake_br.bothify(text="??#######").upper()
            passaportes_usados.add(pass_raw)
            passaporte = pass_raw

        pessoas.append({
            "id": p_id,
            "nome": nome,
            "cpf": cpf,
            "passaporte": passaporte,
            "email": email,
            "dt_nascimento": dt_nascimento,
            "pais": pais,
            "uf": uf,
            "is_brasileiro": is_brasileiro,
        })

        sql_statements.append(
            f"INSERT INTO Pessoa (id, nome, cpf, passaporte, email, dt_nascimento, pais, uf) VALUES "
            f"({sql_val(p_id)}, {sql_val(nome)}, {sql_val(cpf)}, {sql_val(passaporte)}, "
            f"{sql_val(email)}, {sql_val(dt_nascimento)}, {sql_val(pais)}, {sql_val(uf)});"
        )

    # ==========================================================
    # 2. ASSOCIACAO_A_SBTC
    # ==========================================================
    add_section_header("2. TABELA Associacao_a_SBTC")
    # Vigências de mês, semestre e ano, cobrindo o período de 2019 até 2028
    associacoes = []
    associacoes_set = set()

    def gerar_periodo_associacao(ano: int, tipo_vig: str) -> tuple[datetime.date, datetime.date]:
        """Gera datas de início e fim conforme a modalidade de vigência."""
        if tipo_vig == "ano":
            if random.random() < 0.70:
                # Ano civil completo (01/01 a 31/12)
                dt_ini = datetime.date(ano, 1, 1)
                dt_ter = datetime.date(ano, 12, 31)
            else:
                # Anuidade contínua (365 dias)
                mes = random.randint(1, 12)
                dia = random.randint(1, 28)
                dt_ini = datetime.date(ano, mes, dia)
                dt_ter = dt_ini + datetime.timedelta(days=365)
        elif tipo_vig == "semestre":
            if random.random() < 0.70:
                # Semestre civil (1º semestre: jan-jun ou 2º semestre: jul-dez)
                if random.choice([1, 2]) == 1:
                    dt_ini = datetime.date(ano, 1, 1)
                    dt_ter = datetime.date(ano, 6, 30)
                else:
                    dt_ini = datetime.date(ano, 7, 1)
                    dt_ter = datetime.date(ano, 12, 31)
            else:
                # Semestralidade contínua (~180 dias)
                mes = random.randint(1, 12)
                dia = random.randint(1, 28)
                dt_ini = datetime.date(ano, mes, dia)
                dt_ter = dt_ini + datetime.timedelta(days=180)
        else:  # "mes"
            mes = random.randint(1, 12)
            if random.random() < 0.70:
                # Mês civil (do dia 1 ao último dia do mês)
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                dt_ini = datetime.date(ano, mes, 1)
                dt_ter = datetime.date(ano, mes, ultimo_dia)
            else:
                # Mensalidade contínua (30 dias)
                dia = random.randint(1, 28)
                dt_ini = datetime.date(ano, mes, dia)
                dt_ter = dt_ini + datetime.timedelta(days=30)
        return dt_ini, dt_ter

    tipos_vigencia = ["ano", "semestre", "mes"]
    pesos_vigencia = [0.45, 0.35, 0.20]

    for p in pessoas:
        # ~55% das pessoas possuem histórico de associação
        if random.random() < 0.55:
            qtd_periodos = random.choice([1, 2, 3, 4])
            anos_disponiveis = list(range(2019, 2029))  # 2019 até 2028 inclusive
            random.shuffle(anos_disponiveis)

            periodos_pessoa = []

            for ano_candidato in anos_disponiveis:
                if len(periodos_pessoa) >= qtd_periodos:
                    break

                # Tenta gerar um período válido sem sobreposição para esta pessoa
                for _ in range(6):
                    tipo_vig = random.choices(tipos_vigencia, weights=pesos_vigencia)[0]
                    dt_inicio, dt_fim = gerar_periodo_associacao(ano_candidato, tipo_vig)

                    # Garante que não haja sobreposição de datas para a mesma pessoa
                    sobrepoe = any(
                        dt_inicio <= fim and dt_fim >= inicio
                        for inicio, fim in periodos_pessoa
                    )
                    if not sobrepoe:
                        chave = (p["id"], dt_inicio, dt_fim)
                        if chave not in associacoes_set:
                            associacoes_set.add(chave)
                            periodos_pessoa.append((dt_inicio, dt_fim))
                            associacoes.append({
                                "id_pessoa": p["id"],
                                "dt_inicio": dt_inicio,
                                "dt_fim": dt_fim,
                                "tipo_vigencia": tipo_vig,
                            })
                            sql_statements.append(
                                f"INSERT INTO Associacao_a_SBTC (id_pessoa, dt_inicio, dt_fim) VALUES "
                                f"({sql_val(p['id'])}, {sql_val(dt_inicio)}, {sql_val(dt_fim)});"
                            )
                            break

    # ==========================================================
    # 3. EVENTO
    # ==========================================================
    add_section_header("3. TABELA Evento")
    familias_agregadoras = [
        {
            "agregador": {"sigla": "BRACIS", "nome": "Brazilian Conference on Intelligent Systems", "tipo": "Congresso"},
            "agregados": [
                {"sigla": "ENIAC", "nome": "Encontro Nacional de Inteligência Artificial e Computacional", "tipo": "Encontro"},
                {"sigla": "KDMiLe", "nome": "Symposium on Knowledge Discovery, Mining and Learning", "tipo": "Simpósio"},
                {"sigla": "STIL", "nome": "Simpósio de Tecnologia da Informação e da Linguagem Humana", "tipo": "Simpósio"},
                {"sigla": "CTIC-IA", "nome": "Concurso de Trabalhos de Iniciação Científica em Inteligência Artificial", "tipo": "Concurso"},
                {"sigla": "WAI", "nome": "Workshop de Inteligência Artificial Responsável e Ética", "tipo": "Workshop"},
                {"sigla": "BBRC", "nome": "Brazilian Robotics Conference", "tipo": "Conferência"},
            ],
        },
        {
            "agregador": {"sigla": "CSBC", "nome": "Congresso da Sociedade Brasileira de Computação", "tipo": "Congresso"},
            "agregados": [
                {"sigla": "SEMISH", "nome": "Seminário Integrado de Software e Hardware", "tipo": "Seminário"},
                {"sigla": "CTIC", "nome": "Concurso de Trabalhos de Iniciação Científica", "tipo": "Workshop"},
                {"sigla": "WEI", "nome": "Workshop sobre Educação em Computação", "tipo": "Workshop"},
                {"sigla": "WIT", "nome": "Mulheres na Tecnologia da Informação", "tipo": "Workshop"},
                {"sigla": "WPerformance", "nome": "Workshop em Desempenho de Sistemas Computacionais e de Comunicação", "tipo": "Workshop"},
                {"sigla": "WCGA", "nome": "Workshop de Computação em Grade e Aplicações", "tipo": "Workshop"},
                {"sigla": "ETC", "nome": "Encontro de Teoria da Computação", "tipo": "Encontro"},
            ],
        },
        {
            "agregador": {"sigla": "CBSoft", "nome": "Congresso Brasileiro de Software: Teoria e Prática", "tipo": "Congresso"},
            "agregados": [
                {"sigla": "SBES", "nome": "Simpósio Brasileiro de Engenharia de Software", "tipo": "Simpósio"},
                {"sigla": "SBLP", "nome": "Simpósio Brasileiro de Linguagens de Programação", "tipo": "Simpósio"},
                {"sigla": "SAST", "nome": "Simpósio Brasileiro de Teste de Software Sistemático", "tipo": "Simpósio"},
                {"sigla": "VEM", "nome": "Workshop sobre Visualização, Evolução e Manutenção de Software", "tipo": "Workshop"},
                {"sigla": "WTDSoft", "nome": "Workshop de Teses e Dissertações em Engenharia de Software", "tipo": "Workshop"},
            ],
        },
        {
            "agregador": {"sigla": "CBIE", "nome": "Congresso Brasileiro de Informática na Educação", "tipo": "Congresso"},
            "agregados": [
                {"sigla": "SBIE", "nome": "Simpósio Brasileiro de Informática na Educação", "tipo": "Simpósio"},
                {"sigla": "WIE", "nome": "Workshop de Informática na Escola", "tipo": "Workshop"},
                {"sigla": "CTIE", "nome": "Concurso de Teses e Dissertações em Informática na Educação", "tipo": "Concurso"},
            ],
        },
        {
            "agregador": {"sigla": "SBBD", "nome": "Simpósio Brasileiro de Bancos de Dados", "tipo": "Simpósio"},
            "agregados": [
                {"sigla": "BraSNAM", "nome": "Brazilian Workshop on Social Network Analysis and Mining", "tipo": "Workshop"},
                {"sigla": "WGID", "nome": "Workshop de Governança e Inteligência de Dados", "tipo": "Workshop"},
                {"sigla": "WDataScience", "nome": "Workshop Brasileiro de Ciência de Dados e Big Data", "tipo": "Workshop"},
                {"sigla": "WTDBD", "nome": "Workshop de Teses e Dissertações em Bancos de Dados", "tipo": "Workshop"},
            ],
        },
        {
            "agregador": {"sigla": "SBRC", "nome": "Simpósio Brasileiro de Redes de Computadores e Sistemas Distribuídos", "tipo": "Simpósio"},
            "agregados": [
                {"sigla": "WBL", "nome": "Workshop de Blockchain: Teoria, Tecnologias e Aplicações", "tipo": "Workshop"},
                {"sigla": "WCloud", "nome": "Workshop de Computação em Nuvem e Aplicações", "tipo": "Workshop"},
                {"sigla": "WIoT", "nome": "Workshop de Internet das Coisas e Sistemas Ciberfísicos", "tipo": "Workshop"},
                {"sigla": "WTICG", "nome": "Workshop de Tecnologia da Informação e Comunicação dos Governos", "tipo": "Workshop"},
            ],
        },
    ]

    eventos_avulsos = [
        {"sigla": "SIBGRAPI", "nome": "Conferência sobre Gráficos, Padrões e Imagens", "tipo": "Conferência"},
        {"sigla": "SBGames", "nome": "Simpósio Brasileiro de Jogos e Entretenimento Digital", "tipo": "Simpósio"},
        {"sigla": "SBSeg", "nome": "Simpósio Brasileiro de Segurança da Informação e de Sistemas Computacionais", "tipo": "Simpósio"},
        {"sigla": "IHC", "nome": "Simpósio Brasileiro sobre Fatores Humanos em Sistemas Computacionais", "tipo": "Simpósio"},
        {"sigla": "WSCAD", "nome": "Simpósio em Sistemas Computacionais de Alto Desempenho", "tipo": "Simpósio"},
        {"sigla": "SBSI", "nome": "Simpósio Brasileiro de Sistemas de Informação", "tipo": "Simpósio"},
        {"sigla": "SBR", "nome": "Simpósio Brasileiro de Robótica", "tipo": "Simpósio"},
        {"sigla": "SBCM", "nome": "Simpósio Brasileiro de Computação Musical", "tipo": "Simpósio"},
        {"sigla": "BSB", "nome": "Simpósio Brasileiro de Bioinformática e Biologia Computacional", "tipo": "Simpósio"},
        {"sigla": "SBESC", "nome": "Simpósio Brasileiro de Engenharia de Sistemas Computacionais", "tipo": "Simpósio"},
        {"sigla": "ERBASE", "nome": "Escola Regional de Computação Bahia - Alagoas - Sergipe", "tipo": "Escola Regional"},
        {"sigla": "ERAD", "nome": "Escola Regional de Alto Desempenho", "tipo": "Escola Regional"},
        {"sigla": "ERC", "nome": "Escola Regional de Redes de Computadores", "tipo": "Escola Regional"},
        {"sigla": "ERIA", "nome": "Escola Regional de Inteligência Artificial", "tipo": "Escola Regional"},
        {"sigla": "ERBD", "nome": "Escola Regional de Banco de Dados", "tipo": "Escola Regional"},
        {"sigla": "ERSI", "nome": "Escola Regional de Sistemas de Informação", "tipo": "Escola Regional"},
        {"sigla": "EREC", "nome": "Escola Regional de Ensino de Computação", "tipo": "Escola Regional"},
        {"sigla": "ERSEG", "nome": "Escola Regional de Segurança da Informação", "tipo": "Escola Regional"},
        {"sigla": "EROC", "nome": "Escola Regional de Otimização e Computação", "tipo": "Escola Regional"},
        {"sigla": "ERMAC", "nome": "Escola Regional de Matemática Aplicada e Computacional", "tipo": "Escola Regional"},
    ]

    cidades_estados = [
        # Bahia (foco regional)
        ("Salvador", "BA"),
        ("Feira de Santana", "BA"),
        ("Vitória da Conquista", "BA"),
        ("Ilhéus", "BA"),
        ("Itabuna", "BA"),
        ("Juazeiro", "BA"),
        ("Porto Seguro", "BA"),
        ("Camaçari", "BA"),
        ("Lauro de Freitas", "BA"),
        ("Barreiras", "BA"),

        # Nordeste
        ("Aracaju", "SE"),
        ("Maceió", "AL"),
        ("Arapiraca", "AL"),
        ("Recife", "PE"),
        ("Olinda", "PE"),
        ("Caruaru", "PE"),
        ("Petrolina", "PE"),
        ("João Pessoa", "PB"),
        ("Campina Grande", "PB"),
        ("Natal", "RN"),
        ("Mossoró", "RN"),
        ("Fortaleza", "CE"),
        ("Sobral", "CE"),
        ("Juazeiro do Norte", "CE"),
        ("Teresina", "PI"),
        ("Parnaíba", "PI"),
        ("São Luís", "MA"),
        ("Imperatriz", "MA"),

        # Sudeste
        ("São Paulo", "SP"),
        ("Campinas", "SP"),
        ("São Carlos", "SP"),
        ("Ribeirão Preto", "SP"),
        ("São José dos Campos", "SP"),
        ("Santos", "SP"),
        ("Sorocaba", "SP"),
        ("Piracicaba", "SP"),
        ("Bauru", "SP"),
        ("Rio de Janeiro", "RJ"),
        ("Niterói", "RJ"),
        ("Petrópolis", "RJ"),
        ("Campos dos Goytacazes", "RJ"),
        ("Belo Horizonte", "MG"),
        ("Uberlândia", "MG"),
        ("Ouro Preto", "MG"),
        ("Juiz de Fora", "MG"),
        ("Viçosa", "MG"),
        ("Santa Rita do Sapucaí", "MG"),
        ("Montes Claros", "MG"),
        ("Vitória", "ES"),
        ("Vila Velha", "ES"),

        # Sul
        ("Curitiba", "PR"),
        ("Londrina", "PR"),
        ("Maringá", "PR"),
        ("Foz do Iguaçu", "PR"),
        ("Cascavel", "PR"),
        ("Ponta Grossa", "PR"),
        ("Florianópolis", "SC"),
        ("Joinville", "SC"),
        ("Blumenau", "SC"),
        ("Chapecó", "SC"),
        ("Criciúma", "SC"),
        ("Lages", "SC"),
        ("Porto Alegre", "RS"),
        ("Santa Maria", "RS"),
        ("Pelotas", "RS"),
        ("Caxias do Sul", "RS"),
        ("Passo Fundo", "RS"),
        ("Rio Grande", "RS"),

        # Centro-Oeste
        ("Brasília", "DF"),
        ("Goiânia", "GO"),
        ("Anápolis", "GO"),
        ("Rio Verde", "GO"),
        ("Cuiabá", "MT"),
        ("Rondonópolis", "MT"),
        ("Campo Grande", "MS"),
        ("Dourados", "MS"),

        # Norte
        ("Manaus", "AM"),
        ("Belém", "PA"),
        ("Santarém", "PA"),
        ("Palmas", "TO"),
        ("Porto Velho", "RO"),
        ("Rio Branco", "AC"),
        ("Boa Vista", "RR"),
        ("Macapá", "AP"),
    ]

    def sortear_nomes_lotes(qtd: int) -> list[str]:
        """Gera nomes diversificados e contextuais para os lotes de um evento."""
        templates = {
            1: [
                ["Lote Único"],
                ["Inscrição Geral"],
                ["Lote Geral"],
                ["Lote Padrão"],
                ["Inscrição Regular"],
                ["Lote Promocional Único"],
                ["Tarifa Geral"],
            ],
            2: [
                ["1º Lote", "2º Lote"],
                ["Lote Antecipado", "Lote Regular"],
                ["Lote Promocional", "Lote Geral"],
                ["Inscrição Antecipada", "Inscrição Regular"],
                ["Lote Promocional", "Lote Final"],
                ["1º Lote (Online)", "2º Lote (No Local)"],
                ["Fase 1 (Antecipada)", "Fase 2 (Regular)"],
                ["Early Bird", "Regular"],
            ],
            3: [
                ["1º Lote (Promocional)", "2º Lote (Regular)", "3º Lote (Última Hora)"],
                ["Lote Antecipado", "Lote Regular", "Lote Tardio"],
                ["1º Lote", "2º Lote", "3º Lote"],
                ["Lote Promocional", "Lote Padrão", "Lote Final"],
                ["Lote de Lançamento", "Lote Ordinário", "Lote de Encerramento"],
                ["Fase 1 (Promocional)", "Fase 2 (Regular)", "Fase 3 (No Local)"],
                ["Early Bird", "Standard", "Late / On-site"],
                ["1º Período", "2º Período", "3º Período"],
            ],
            4: [
                ["1º Lote (Promocional)", "2º Lote (Regular)", "3º Lote (Última Hora)", "4º Lote (No Local)"],
                ["Lote Promocional", "Lote Padrão", "Lote Reta Final", "Inscrições no Credenciamento"],
                ["1º Lote", "2º Lote", "3º Lote", "4º Lote"],
                ["Lote Antecipado", "Lote Regular", "Lote Tardio", "Inscrição Presencial"],
                ["Fase 1 (Lançamento)", "Fase 2 (Regular)", "Fase 3 (Última Chamada)", "Fase 4 (No Local)"],
                ["Early Bird", "Standard", "Late", "On-site"],
                ["1º Lote Promocional", "2º Lote Regular", "3º Lote Prorrogado", "4º Lote no Local"],
            ],
        }
        opcoes = templates.get(qtd)
        return random.choice(opcoes) if opcoes else [f"{i}º Lote" for i in range(1, qtd + 1)]

    # Planejamento dos eventos: seleciona famílias agregadoras e eventos satélites
    # Garante que haja eventos agregadores (como BRACIS) e seus respectivos eventos agregados
    plano_eventos = []

    familias_candidatas = list(familias_agregadoras)
    # Garante BRACIS prioritariamente no início
    idx_bracis = next(i for i, f in enumerate(familias_candidatas) if f["agregador"]["sigla"] == "BRACIS")
    familias_candidatas.insert(0, familias_candidatas.pop(idx_bracis))

    idx_fam = 0
    idx_avulso = 0
    avulsos_embaralhados = random.sample(eventos_avulsos, len(eventos_avulsos))

    while len(plano_eventos) < num_eventos:
        if idx_fam < len(familias_candidatas):
            fam = familias_candidatas[idx_fam]
            idx_fam += 1

            # 1. Adiciona o evento agregador (ex: BRACIS, CSBC, CBSoft)
            idx_pai = len(plano_eventos)
            plano_eventos.append({"modelo": fam["agregador"], "idx_agregador": None})

            # 2. Adiciona de 1 a 3 eventos agregados deste agregador
            agregados_embaralhados = random.sample(fam["agregados"], len(fam["agregados"]))
            qtd_agregados = min(random.randint(1, 3), len(agregados_embaralhados), num_eventos - len(plano_eventos))
            for k in range(qtd_agregados):
                plano_eventos.append({"modelo": agregados_embaralhados[k], "idx_agregador": idx_pai})

            if len(plano_eventos) >= num_eventos:
                break

            # 3. Ocasionalmente intercala um evento avulso (ex: Escola Regional)
            if random.random() < 0.40 and len(plano_eventos) < num_eventos:
                plano_eventos.append({
                    "modelo": avulsos_embaralhados[idx_avulso % len(avulsos_embaralhados)],
                    "idx_agregador": None,
                })
                idx_avulso += 1
        else:
            plano_eventos.append({
                "modelo": avulsos_embaralhados[idx_avulso % len(avulsos_embaralhados)],
                "idx_agregador": None,
            })
            idx_avulso += 1

    eventos = []
    # Gera cada evento conforme o plano estabelecido
    for e_idx, item in enumerate(plano_eventos):
        e_id = e_idx + 1
        modelo = item["modelo"]
        edicao_num = random.randint(1, 45)
        edicao = f"{edicao_num}ª Edição"

        if item["idx_agregador"] is None:
            # Evento independente ou agregador principal (ex: BRACIS, CSBC)
            cidade, estado = random.choice(cidades_estados)
            ano = random.choice([2024, 2025, 2026, 2027])
            mes = random.randint(1, 12)
            dia = random.randint(1, 28)
            dt_inicio = datetime.date(ano, mes, dia)
            duracao = random.randint(4, 6)
            dt_fim = dt_inicio + datetime.timedelta(days=duracao)
            modalidade = random.choice(["Presencial", "Híbrido", "Online"])
            id_agregado_por = None
            descricao = f"{modelo['nome']} - {edicao}. Fórum acadêmico e profissional em {cidade}/{estado}."
        else:
            # Evento agregado: herda localidade, ano e datas do evento agregador
            agregador = eventos[item["idx_agregador"]]
            id_agregado_por = agregador["id"]
            cidade = agregador["cidade"]
            estado = agregador["estado"]
            ano = agregador["ano"]
            modalidade = agregador["modalidade_edicao"]
            dt_inicio = agregador["dt_inicio"]
            dt_fim = agregador["dt_fim"]
            descricao = f"{modelo['nome']} - {edicao}. Evento satélite integrado ao {agregador['sigla']} {agregador['ano']} em {cidade}/{estado}."

        # Geração de lotes de inscrição com deltas, quantidades e datas independentes por evento
        # Um evento pode ter de 1 até 4 lotes
        num_lotes = random.choices([1, 2, 3, 4], weights=[0.15, 0.25, 0.35, 0.25])[0]
        nomes_lotes = sortear_nomes_lotes(num_lotes)

        # Cada evento define sua própria antecedência de início de vendas
        antecedencia_dias = random.randint(60, 190)
        data_cursor = dt_inicio - datetime.timedelta(days=antecedencia_dias)

        preco_lote_atual = Decimal(random.randint(110, 220))
        lotes_evento = []

        for i in range(num_lotes):
            dt_ini_lote = data_cursor
            nome_lote = nomes_lotes[i]

            if i == num_lotes - 1:
                # Último lote do evento (ou lote único se num_lotes == 1)
                if num_lotes == 1:
                    # Lote único cobre até a véspera ou o encerramento do evento
                    if random.random() < 0.60:
                        dt_fim_lote = dt_fim
                    else:
                        dias_antes_evento = random.randint(1, 3)
                        dt_fim_lote = max(dt_ini_lote, dt_inicio - datetime.timedelta(days=dias_antes_evento))
                elif i == 3 or random.random() < 0.60:
                    dt_fim_lote = dt_fim
                else:
                    dias_antes_evento = random.randint(1, 4)
                    dt_fim_lote = max(dt_ini_lote, dt_inicio - datetime.timedelta(days=dias_antes_evento))
            else:
                # Lotes intermediários com duração calculada independentemente
                dias_ate_evento = (dt_inicio - dt_ini_lote).days
                lotes_restantes = num_lotes - 1 - i
                margem_seguranca = lotes_restantes * 7
                dias_disponiveis = max(10, dias_ate_evento - margem_seguranca)

                duracao_base = dias_disponiveis // (lotes_restantes + 1)
                duracao_lote = random.randint(
                    max(7, int(duracao_base * 0.65)),
                    max(10, int(duracao_base * 1.35))
                )
                dt_fim_lote = dt_ini_lote + datetime.timedelta(days=duracao_lote)

                limite_max = dt_inicio - datetime.timedelta(days=margem_seguranca)
                if dt_fim_lote > limite_max:
                    dt_fim_lote = limite_max
                if dt_fim_lote < dt_ini_lote:
                    dt_fim_lote = dt_ini_lote + datetime.timedelta(days=5)

            lotes_evento.append({
                "numero": i + 1,
                "nome": nome_lote,
                "dt_inicio": dt_ini_lote,
                "dt_fim": dt_fim_lote,
                "preco": preco_lote_atual,
            })

            preco_lote_atual = preco_lote_atual + Decimal(random.randint(40, 85))
            intervalo_gap = random.choice([1, 1, 1, 2])
            data_cursor = dt_fim_lote + datetime.timedelta(days=intervalo_gap)

        lote_1 = lotes_evento[0]
        lote_2 = lotes_evento[1] if len(lotes_evento) > 1 else None
        lote_3 = lotes_evento[2] if len(lotes_evento) > 2 else None
        lote_4 = lotes_evento[3] if len(lotes_evento) > 3 else None

        evento_dict = {
            "id": e_id,
            "ano": ano,
            "dt_inicio": dt_inicio,
            "dt_fim": dt_fim,
            "modalidade_edicao": modalidade,
            "lotes": lotes_evento,
            "nome_lote_1": lote_1["nome"],
            "dt_inicio_lote_1": lote_1["dt_inicio"],
            "dt_fim_lote_1": lote_1["dt_fim"],
            "preco_base_lote_1": lote_1["preco"],
            "nome_lote_2": lote_2["nome"] if lote_2 else None,
            "dt_inicio_lote_2": lote_2["dt_inicio"] if lote_2 else None,
            "dt_fim_lote_2": lote_2["dt_fim"] if lote_2 else None,
            "preco_base_lote_2": lote_2["preco"] if lote_2 else None,
            "nome_lote_3": lote_3["nome"] if lote_3 else None,
            "dt_inicio_lote_3": lote_3["dt_inicio"] if lote_3 else None,
            "dt_fim_lote_3": lote_3["dt_fim"] if lote_3 else None,
            "preco_base_lote_3": lote_3["preco"] if lote_3 else None,
            "nome_lote_4": lote_4["nome"] if lote_4 else None,
            "dt_inicio_lote_4": lote_4["dt_inicio"] if lote_4 else None,
            "dt_fim_lote_4": lote_4["dt_fim"] if lote_4 else None,
            "preco_base_lote_4": lote_4["preco"] if lote_4 else None,
            "sigla": modelo["sigla"],
            "nome": modelo["nome"],
            "descricao": descricao,
            "cidade": cidade,
            "estado": estado,
            "pais": "BRA",
            "edicao": edicao,
            "tipo": modelo["tipo"],
            "id_agregado_por": id_agregado_por,
        }
        eventos.append(evento_dict)

        sql_statements.append(
            f"INSERT INTO Evento ("
            f"id, ano, dt_inicio, dt_fim, modalidade_edicao, "
            f"nome_lote_1, dt_inicio_lote_1, dt_fim_lote_1, preco_base_lote_1, "
            f"nome_lote_2, dt_inicio_lote_2, dt_fim_lote_2, preco_base_lote_2, "
            f"nome_lote_3, dt_inicio_lote_3, dt_fim_lote_3, preco_base_lote_3, "
            f"nome_lote_4, dt_inicio_lote_4, dt_fim_lote_4, preco_base_lote_4, "
            f"sigla, nome, descricao, cidade, estado, pais, edicao, tipo, id_agregado_por"
            f") VALUES ("
            f"{sql_val(e_id)}, {sql_val(ano)}, {sql_val(dt_inicio)}, {sql_val(dt_fim)}, {sql_val(modalidade)}, "
            f"{sql_val(lote_1['nome'])}, {sql_val(lote_1['dt_inicio'])}, {sql_val(lote_1['dt_fim'])}, {sql_val(lote_1['preco'])}, "
            f"{sql_val(lote_2['nome'] if lote_2 else None)}, {sql_val(lote_2['dt_inicio'] if lote_2 else None)}, {sql_val(lote_2['dt_fim'] if lote_2 else None)}, {sql_val(lote_2['preco'] if lote_2 else None)}, "
            f"{sql_val(lote_3['nome'] if lote_3 else None)}, {sql_val(lote_3['dt_inicio'] if lote_3 else None)}, {sql_val(lote_3['dt_fim'] if lote_3 else None)}, {sql_val(lote_3['preco'] if lote_3 else None)}, "
            f"{sql_val(lote_4['nome'] if lote_4 else None)}, {sql_val(lote_4['dt_inicio'] if lote_4 else None)}, {sql_val(lote_4['dt_fim'] if lote_4 else None)}, {sql_val(lote_4['preco'] if lote_4 else None)}, "
            f"{sql_val(modelo['sigla'])}, {sql_val(modelo['nome'])}, {sql_val(descricao)}, "
            f"{sql_val(cidade)}, {sql_val(estado)}, 'BRA', {sql_val(edicao)}, {sql_val(modelo['tipo'])}, "
            f"{sql_val(id_agregado_por)});"
        )

    # ==========================================================
    # 4. REGRA_REEMBOLSO
    # ==========================================================
    add_section_header("4. TABELA Regra_reembolso")
    for ev in eventos:
        # Políticas de reembolso independentes e dinâmicas por evento:
        # - Nem todos os eventos possuem regras de reembolso (política não reembolsável)
        # - Quantidade de regras varia de 0 até 4 regras
        # - Nem todos reembolsam 100% (tetos variam entre 70%, 80%, 85%, 90% e 100%)
        # - Percentuais decrescem à medida que a data do evento se aproxima
        qtd_regras = random.choices([0, 1, 2, 3, 4], weights=[0.20, 0.25, 0.30, 0.18, 0.07])[0]

        regras_evento = []
        if qtd_regras > 0:
            # Sorteia prazos distintos em dias de antecedência (ex: de 5 a 85 dias antes de dt_inicio)
            dias_sorteados = sorted(random.sample(range(5, 85), qtd_regras), reverse=True)

            # Teto máximo de reembolso para o prazo mais antecipado
            tetos_possiveis = [
                Decimal("1.0000000"),
                Decimal("0.9000000"),
                Decimal("0.8500000"),
                Decimal("0.8000000"),
                Decimal("0.7500000"),
                Decimal("0.7000000"),
            ]
            teto = random.choice(tetos_possiveis)

            if qtd_regras == 1:
                percentuais = [teto]
            elif qtd_regras == 2:
                segundo_grau = Decimal(f"{float(teto) * random.uniform(0.40, 0.65):.2f}00000")
                percentuais = [teto, segundo_grau]
            elif qtd_regras == 3:
                segundo_grau = Decimal(f"{float(teto) * random.uniform(0.60, 0.75):.2f}00000")
                terceiro_grau = Decimal(f"{float(segundo_grau) * random.uniform(0.40, 0.60):.2f}00000")
                percentuais = [teto, segundo_grau, terceiro_grau]
            else:  # 4 regras
                p2 = Decimal(f"{float(teto) * random.uniform(0.70, 0.85):.2f}00000")
                p3 = Decimal(f"{float(p2) * random.uniform(0.55, 0.75):.2f}00000")
                p4 = Decimal(f"{float(p3) * random.uniform(0.40, 0.60):.2f}00000")
                percentuais = [teto, p2, p3, p4]

            # Registra as regras no evento e gera os comandos SQL
            for dias, pct in zip(dias_sorteados, percentuais):
                dt_limite = ev["dt_inicio"] - datetime.timedelta(days=dias)
                regras_evento.append((dt_limite, pct))
                sql_statements.append(
                    f"INSERT INTO Regra_reembolso (id_evento, dt_limite, pct_devolvida) VALUES "
                    f"({sql_val(ev['id'])}, {sql_val(dt_limite)}, {sql_val(pct)});"
                )

        ev["regras_reembolso"] = regras_evento

    # ==========================================================
    # 5. CATEGORIA_INSCRICAO
    # ==========================================================
    add_section_header("5. TABELA Categoria_inscricao")
    cat_templates = [
        {"nome": "Estudante de Graduação", "desc": "Comprovante de matrícula obrigatório", "fator": Decimal("0.5000000")},
        {"nome": "Estudante de Pós-Graduação", "desc": "Comprovante de pós-graduação obrigatório", "fator": Decimal("0.7000000")},
        {"nome": "Profissional Associado SBTC", "desc": "Desconto exclusivo para membros ativos da SBTC", "fator": Decimal("0.8000000")},
        {"nome": "Profissional Não Associado", "desc": "Inscrição padrão da categoria profissional", "fator": Decimal("1.0000000")},
        {"nome": "Palestrante / Autor Convidado", "desc": "Inscrição isenta para palestrantes convidados", "fator": Decimal("0.0000000")},
    ]

    categorias = []
    cat_id_counter = 1
    for ev in eventos:
        for tpl in cat_templates:
            cat_obj = {
                "id": cat_id_counter,
                "id_evento": ev["id"],
                "nome": tpl["nome"],
                "descricao": tpl["desc"],
                "fator_mult_preco": tpl["fator"],
            }
            categorias.append(cat_obj)
            sql_statements.append(
                f"INSERT INTO Categoria_inscricao (id, fator_mult_preco, nome, descricao, id_evento) VALUES "
                f"({sql_val(cat_id_counter)}, {sql_val(tpl['fator'])}, {sql_val(tpl['nome'])}, "
                f"{sql_val(tpl['desc'])}, {sql_val(ev['id'])});"
            )
            cat_id_counter += 1

    # ==========================================================
    # 6. ATIVIDADE
    # ==========================================================
    add_section_header("6. TABELA Atividade")
    tipos_atividades = ["Palestra", "Minicurso", "Mesa Redonda", "Sessão Técnica", "Painel"]
    temas_atividades = [
        "Avanços em Inteligência Artificial Generativa",
        "Modelagem e Otimização em Banco de Dados Relacionais e NoSQL",
        "Segurança da Informação e Privacidade de Dados em Nuvem",
        "Engenharia de Software para Sistemas Críticos",
        "Computação Quântica: Fundamentos e Perspectivas",
        "Sistemas Embarcados e Internet das Coisas (IoT)",
        "Processamento de Linguagem Natural com LLMs",
        "Boas Práticas de DevOps e Arquitetura de Microsserviços",
    ]

    atividades = []
    atv_id_counter = 1
    for ev in eventos:
        # Encontra categorias pertencentes a este evento
        cats_evento = [c for c in categorias if c["id_evento"] == ev["id"]]

        # 3 a 5 atividades por evento
        qtd_atividades = random.randint(3, 5)
        for _ in range(qtd_atividades):
            tipo = random.choice(tipos_atividades)
            tema = random.choice(temas_atividades)
            nome_atv = f"{tipo}: {tema}"
            capacidade = random.choice([40, 60, 100, 150, 250, None])

            # Minicursos costumam ter taxa adicional, palestras geralmente não
            if tipo == "Minicurso" and random.random() < 0.7:
                preco_atv = Decimal(f"{random.randint(30, 80)}.00")
            else:
                preco_atv = Decimal("0.00")

            dia_offset = random.randint(0, (ev["dt_fim"] - ev["dt_inicio"]).days)
            dt_atv_dia = ev["dt_inicio"] + datetime.timedelta(days=dia_offset)
            hora_inicio = random.choice([9, 11, 14, 16, 18])
            dt_inicio_atv = datetime.datetime.combine(dt_atv_dia, datetime.time(hora_inicio, 0))
            dt_fim_atv = dt_inicio_atv + datetime.timedelta(hours=random.choice([1, 2, 3]))

            # Pode ser restrito a uma categoria ou livre (NULL)
            id_cat = random.choice(cats_evento)["id"] if random.random() < 0.3 else None

            atividades.append({
                "id": atv_id_counter,
                "capacidade": capacidade,
                "preco": preco_atv,
                "dt_inicio": dt_inicio_atv,
                "dt_fim": dt_fim_atv,
                "nome": nome_atv,
                "tipo": tipo,
                "id_categoria_inscricao": id_cat,
            })

            sql_statements.append(
                f"INSERT INTO Atividade (id, capacidade, preco, dt_inicio, dt_fim, nome, tipo, id_categoria_inscricao) VALUES "
                f"({sql_val(atv_id_counter)}, {sql_val(capacidade)}, {sql_val(preco_atv)}, "
                f"{sql_val(dt_inicio_atv)}, {sql_val(dt_fim_atv)}, {sql_val(nome_atv)}, "
                f"{sql_val(tipo)}, {sql_val(id_cat)});"
            )
            atv_id_counter += 1

    # ==========================================================
    # 7. INSCRICAO
    # ==========================================================
    add_section_header("7. TABELA Inscricao")
    inscricoes = []
    # Evita que a mesma pessoa se inscreva duas vezes no mesmo evento
    pessoa_evento_inscrita = set()

    inscricao_id = 1
    # Embaralha pessoas e categorias
    tentativas = 0
    max_tentativas = num_inscricoes * 5

    while len(inscricoes) < num_inscricoes and tentativas < max_tentativas:
        tentativas += 1
        pessoa = random.choice(pessoas)
        categoria = random.choice(categorias)
        ev = next(e for e in eventos if e["id"] == categoria["id_evento"])

        par_chave = (pessoa["id"], ev["id"])
        if par_chave in pessoa_evento_inscrita:
            continue
        pessoa_evento_inscrita.add(par_chave)

        # Escolhe a data de inscrição dentro de um dos lotes válidos deste evento
        lotes_disp = ev["lotes"]
        pesos_lotes = [0.50, 0.35, 0.12, 0.03][:len(lotes_disp)]
        lote_escolhido = random.choices(lotes_disp, weights=pesos_lotes)[0]

        dias_max = max(0, (lote_escolhido["dt_fim"] - lote_escolhido["dt_inicio"]).days)
        dt_insc = lote_escolhido["dt_inicio"] + datetime.timedelta(days=random.randint(0, dias_max))
        preco_base = lote_escolhido["preco"]

        dt_inscricao = datetime.datetime.combine(
            dt_insc,
            datetime.time(random.randint(8, 22), random.randint(0, 59), random.randint(0, 59))
        )

        # ~80% das inscrições são confirmadas (pagas), ~20% pendentes ou canceladas
        is_confirmada = random.random() < 0.80
        if is_confirmada:
            delta_minutos = random.randint(5, 2880)  # até 2 dias para confirmar
            dt_confirmacao = dt_inscricao + datetime.timedelta(minutes=delta_minutos)
        else:
            dt_confirmacao = None

        inscricao_dict = {
            "id": inscricao_id,
            "dt_confirmacao": dt_confirmacao,
            "dt_inscricao": dt_inscricao,
            "id_categoria": categoria["id"],
            "id_pessoa": pessoa["id"],
            "preco_base": preco_base,
            "fator_mult": categoria["fator_mult_preco"],
            "id_evento": ev["id"],
            "evento_sigla": ev["sigla"],
            "evento_ano": ev["ano"],
            "categoria_nome": categoria["nome"],
            "lote_nome": lote_escolhido["nome"],
        }
        inscricoes.append(inscricao_dict)

        sql_statements.append(
            f"INSERT INTO Inscricao (id, dt_confirmacao, dt_inscricao, id_categoria, id_pessoa) VALUES "
            f"({sql_val(inscricao_id)}, {sql_val(dt_confirmacao)}, {sql_val(dt_inscricao)}, "
            f"{sql_val(categoria['id'])}, {sql_val(pessoa['id'])});"
        )
        inscricao_id += 1

    # ==========================================================
    # 8. ITEM_FINANCEIRO
    # ==========================================================
    add_section_header("8. TABELA Item_financeiro")
    itens_financeiros = []

    for item_id, insc in enumerate(inscricoes, start=1):
        if insc["dt_confirmacao"] is not None:
            # Confirmada: houve pagamento
            dt_pagamento = insc["dt_confirmacao"]
            # Pequena taxa de cancelamento após pagamento (~5%) para testar estornos/reembolsos
            if random.random() < 0.05:
                dt_cancelamento = dt_pagamento + datetime.timedelta(days=random.randint(1, 10))
            else:
                dt_cancelamento = None
        else:
            # Não confirmada: pendente ou cancelada antes de pagar
            dt_pagamento = None
            if random.random() < 0.5:
                # Cancelada sem pagamento
                dt_cancelamento = insc["dt_inscricao"] + datetime.timedelta(days=random.randint(3, 7))
            else:
                # Permanece pendente
                dt_cancelamento = None

        valor_calculado = Decimal(f"{(insc['preco_base'] * insc['fator_mult']):.2f}")
        tipo_item = "Inscrição"
        descricao_item = f"Inscrição {insc['evento_sigla']} {insc['evento_ano']} - {insc['categoria_nome']} ({insc['lote_nome']})"

        item_dict = {
            "id": item_id,
            "dt_pagamento": dt_pagamento,
            "dt_cancelamento": dt_cancelamento,
            "id_inscricao": insc["id"],
            "descricao": descricao_item,
            "valor": valor_calculado,
            "tipo": tipo_item,
            "inscricao": insc,
        }
        itens_financeiros.append(item_dict)

        sql_statements.append(
            f"INSERT INTO Item_financeiro (id, dt_pagamento, dt_cancelamento, id_inscricao, descricao, valor, tipo) VALUES "
            f"({sql_val(item_id)}, {sql_val(dt_pagamento)}, {sql_val(dt_cancelamento)}, {sql_val(insc['id'])}, "
            f"{sql_val(descricao_item)}, {sql_val(valor_calculado)}, {sql_val(tipo_item)});"
        )

    # ==========================================================
    # 9. PAGAMENTO
    # ==========================================================
    add_section_header("9. TABELA Pagamento")
    modalidades = ["PIX", "Cartão de Crédito", "Boleto Bancário"]
    pagamentos = []
    cods_transacao_usados = set()
    pagamento_id_counter = 1

    def gerar_cod_transacao(prefixo: str = "TXN") -> str:
        code = f"{prefixo}-{fake_br.bothify(text='????-########').upper()}"
        while code in cods_transacao_usados:
            code = f"{prefixo}-{fake_br.bothify(text='????-########').upper()}"
        cods_transacao_usados.add(code)
        return code

    pagamentos_originais_para_reembolso = []

    for it in itens_financeiros:
        insc = it["inscricao"]
        valor_calculado = Decimal(f"{(insc['preco_base'] * insc['fator_mult']):.2f}")

        # Se houve pagamento ou tentativa de pagamento
        if it["dt_pagamento"] is not None:
            # Pagamento confirmado
            dt_criacao = insc["dt_inscricao"]
            dt_confirmacao = it["dt_pagamento"]
            modalidade = random.choice(modalidades)
            cod_tx = gerar_cod_transacao("PAY")

            pag_obj = {
                "id": pagamento_id_counter,
                "tipo": "Inscrição",
                "valor": valor_calculado,
                "dt_criacao": dt_criacao,
                "dt_confirmacao": dt_confirmacao,
                "cod_transacao": cod_tx,
                "modalidade": modalidade,
                "id_reembolsa": None,
                "id_item_financeiro": it["id"],
            }
            pagamentos.append(pag_obj)

            sql_statements.append(
                f"INSERT INTO Pagamento (id, tipo, valor, dt_criacao, dt_confirmacao, cod_transacao, modalidade, id_reembolsa, id_item_financeiro) VALUES "
                f"({sql_val(pagamento_id_counter)}, {sql_val('Inscrição')}, {sql_val(valor_calculado)}, "
                f"{sql_val(dt_criacao)}, {sql_val(dt_confirmacao)}, {sql_val(cod_tx)}, "
                f"{sql_val(modalidade)}, NULL, {sql_val(it['id'])});"
            )

            # Se o item foi cancelado após o pagamento, gera estorno/reembolso
            if it["dt_cancelamento"] is not None and valor_calculado > 0:
                pagamentos_originais_para_reembolso.append((pagamento_id_counter, it, valor_calculado, insc["id_evento"]))

            pagamento_id_counter += 1

        elif it["dt_cancelamento"] is None:
            # Pagamento ainda pendente de confirmação
            dt_criacao = insc["dt_inscricao"]
            dt_confirmacao = None
            modalidade = random.choice(modalidades)
            cod_tx = gerar_cod_transacao("PEN")

            pag_obj = {
                "id": pagamento_id_counter,
                "tipo": "Inscrição",
                "valor": valor_calculado,
                "dt_criacao": dt_criacao,
                "dt_confirmacao": None,
                "cod_transacao": cod_tx,
                "modalidade": modalidade,
                "id_reembolsa": None,
                "id_item_financeiro": it["id"],
            }
            pagamentos.append(pag_obj)

            sql_statements.append(
                f"INSERT INTO Pagamento (id, tipo, valor, dt_criacao, dt_confirmacao, cod_transacao, modalidade, id_reembolsa, id_item_financeiro) VALUES "
                f"({sql_val(pagamento_id_counter)}, {sql_val('Inscrição')}, {sql_val(valor_calculado)}, "
                f"{sql_val(dt_criacao)}, NULL, {sql_val(cod_tx)}, "
                f"{sql_val(modalidade)}, NULL, {sql_val(it['id'])});"
            )
            pagamento_id_counter += 1

    # Criação dos reembolsos (Pagamentos com id_reembolsa apontando para o id do pagamento original)
    if pagamentos_originais_para_reembolso:
        sql_statements.append("\n-- Reembolsos vinculados a pagamentos originais cancelados")
        for id_orig, it, valor_orig, id_ev in pagamentos_originais_para_reembolso:
            ev_obj = next(e for e in eventos if e["id"] == id_ev)
            regras_ev = ev_obj.get("regras_reembolso", [])

            # Procura a regra de reembolso aplicável com base na data de cancelamento
            dt_canc_date = it["dt_cancelamento"].date()
            pct_aplicada = None
            for dt_limite, pct in regras_ev:
                if dt_canc_date <= dt_limite:
                    pct_aplicada = pct
                    break

            if pct_aplicada is None:
                if not regras_ev:
                    # Evento não prevê reembolso formal, mas estorno parcial administrativo pode ocorrer (~40%)
                    pct_aplicada = Decimal("0.4000000")
                else:
                    # Cancelamento fora do prazo das regras (retenção administrativa com estorno residual)
                    pct_aplicada = Decimal("0.2000000")

            valor_reembolso = Decimal(f"{(valor_orig * pct_aplicada):.2f}")
            if valor_reembolso <= Decimal("0.00"):
                continue

            dt_criacao_ref = it["dt_cancelamento"]
            dt_conf_ref = dt_criacao_ref + datetime.timedelta(hours=random.randint(12, 48))
            cod_tx_ref = gerar_cod_transacao("REF")

            sql_statements.append(
                f"INSERT INTO Pagamento (id, tipo, valor, dt_criacao, dt_confirmacao, cod_transacao, modalidade, id_reembolsa, id_item_financeiro) VALUES "
                f"({sql_val(pagamento_id_counter)}, {sql_val('Reembolso')}, {sql_val(valor_reembolso)}, "
                f"{sql_val(dt_criacao_ref)}, {sql_val(dt_conf_ref)}, {sql_val(cod_tx_ref)}, "
                f"{sql_val('PIX')}, {sql_val(id_orig)}, {sql_val(it['id'])});"
            )
            pagamento_id_counter += 1

    # ==========================================================
    # 10. SINCRONIZAÇÃO DE SEQUENCES DO POSTGRESQL
    # ==========================================================
    add_section_header("10. Ajuste das Sequences de Identity (PostgreSQL)")
    tabelas_identity = [
        "Pessoa",
        "Evento",
        "Categoria_inscricao",
        "Atividade",
        "Inscricao",
        "Item_financeiro",
        "Pagamento",
    ]
    for tab in tabelas_identity:
        tab_lower = tab.lower()
        sql_statements.append(
            f"SELECT setval(pg_get_serial_sequence('{tab_lower}', 'id'), coalesce(max(id), 1)) FROM {tab_lower};"
        )

    sql_statements.append("\nCOMMIT;\n")

    # Salva no arquivo de saída
    conteudo_sql = "\n".join(sql_statements)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(conteudo_sql)

    print(f"Sucesso! Arquivo '{output_file}' gerado com sucesso.")
    print(f"- Pessoas geradas: {len(pessoas)}")
    print(f"- Associações SBTC: {len(associacoes)}")
    print(f"- Eventos: {len(eventos)}")
    print(f"- Categorias: {len(categorias)}")
    print(f"- Atividades: {len(atividades)}")
    print(f"- Inscrições: {len(inscricoes)}")
    print(f"- Itens financeiros: {len(itens_financeiros)}")
    print(f"- Pagamentos (incluindo reembolsos): {pagamento_id_counter - 1}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gera dados sintéticos com Faker e queries de INSERT INTO para o banco de dados."
    )
    parser.add_argument("--pessoas", type=int, default=60, help="Quantidade de pessoas a gerar (padrão: 60)")
    parser.add_argument("--eventos", type=int, default=6, help="Quantidade de eventos a gerar (padrão: 6)")
    parser.add_argument("--inscricoes", type=int, default=100, help="Quantidade de inscrições a gerar (padrão: 100)")
    parser.add_argument("--output", type=str, default="inserts_banco_de_dados.sql", help="Arquivo SQL de saída")
    parser.add_argument("--seed", type=int, default=42, help="Seed aleatória para reproducibilidade")

    args = parser.parse_args()

    gerar_sql(
        num_pessoas=args.pessoas,
        num_eventos=args.eventos,
        num_inscricoes=args.inscricoes,
        output_file=args.output,
        seed=args.seed,
    )