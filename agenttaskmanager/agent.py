
from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime, date, time
import os
import unicodedata
from zoneinfo import ZoneInfo

load_dotenv()

# Credenciais do Trello
API_KEY = os.getenv("TRELLO_API_KEY")
API_SECRET = os.getenv("TRELLO_API_SECRET")
TOKEN = os.getenv("TRELLO_TOKEN")


# ==========================================
# CONEXÃO COM O TRELLO
# ==========================================

def get_trello_client():
    """Cria e retorna o cliente do Trello usando as credenciais do .env."""

    credenciais = {
        "TRELLO_API_KEY": API_KEY,
        "TRELLO_API_SECRET": API_SECRET,
        "TRELLO_TOKEN": TOKEN,
    }

    credenciais_ausentes = [
        nome for nome, valor in credenciais.items() if not valor
    ]

    if credenciais_ausentes:
        raise ValueError(
            "Credenciais ausentes no arquivo .env: "
            + ", ".join(credenciais_ausentes)
        )

    return TrelloClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        token=TOKEN
    )


# ==========================================
# LOCALIZAR QUADROS DO TRELLO
# ==========================================

def obter_quadro(client, nome_quadro: str):
    """Localiza um quadro pelo nome, ignorando diferenças de acentos e caixa."""

    boards = client.list_boards()

    quadro = next(
        (
            board for board in boards
            if normalizar_texto(board.name)
            == normalizar_texto(nome_quadro)
        ),
        None
    )

    return quadro


def listar_quadros():
    """Retorna os quadros disponíveis na conta Trello."""

    try:
        client = get_trello_client()
        boards = client.list_boards()

        if not boards:
            return "Nenhum quadro encontrado na sua conta Trello."

        nomes_quadros = [board.name for board in boards]

        return (
            "📋 Quadros disponíveis no Trello:\n"
            + "\n".join(
                f"- {nome}" for nome in nomes_quadros
            )
        )

    except Exception as e:
        return f"❌ Erro ao consultar quadros: {str(e)}"




# ==========================================
# CONTEXTO TEMPORAL
# ==========================================

def get_temporal_context():
    """Retorna a data e hora atual."""

    fuso_sp = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(fuso_sp)

    return now.strftime("%Y/%m/%d %H:%M:%S")

# ==========================================
# NORMALIZAÇÃO DE TEXTOS E STATUS
# ==========================================

def normalizar_texto(texto: str) -> str:
    """Remove acentos, espaços extras e padroniza letras."""

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return " ".join(texto.lower().strip().split())


# ==========================================
# TRATAMENTO DE DATAS DO TRELLO
# ==========================================

def formatar_data_trello(data_recebida: str) -> str:
    """
    Converte a data recebida para ISO 8601 em UTC,
    preservando o dia escolhido no horário de São Paulo.
    """

    fuso_sp = ZoneInfo("America/Sao_Paulo")

    # Primeiro, tentar interpretar como data YYYY-MM-DD
    try:
        data = date.fromisoformat(data_recebida.strip())

        # Utilizar meio-dia para evitar mudança de dia
        data_local = datetime.combine(
            data,
            time(12, 0),
            tzinfo=fuso_sp
        )

    except ValueError:

        # Aceitar também o formato DD/MM/YYYY
        try:
            data = datetime.strptime(
                data_recebida.strip(),
                "%d/%m/%Y"
            ).date()

            data_local = datetime.combine(
                data,
                time(12, 0),
                tzinfo=fuso_sp
            )

        except ValueError:

            # Caso tenha recebido data e horário
            data_local = datetime.fromisoformat(
                data_recebida.strip().replace("Z", "+00:00")
            )

            # Se não houver fuso, considerar horário de São Paulo
            if data_local.tzinfo is None:
                data_local = data_local.replace(tzinfo=fuso_sp)

    # Converter para UTC
    data_utc = data_local.astimezone(ZoneInfo("UTC"))

    return data_utc.isoformat(timespec="seconds").replace("+00:00", "Z")


def obter_categoria_status(status: str):
    """Identifica a categoria do status, aceitando variações."""

    status = normalizar_texto(status)

    status_aliases = {
        "a fazer": [
            "a fazer",
            "to do",
            "todo",
            "pendente",
            "pendentes"
        ],

        "em andamento": [
            "em andamento",
            "andamento",
            "doing",
            "in progress"
        ],

        "concluido": [
            "concluido",
            "concluida",
            "done",
            "finalizado",
            "finalizada",
            "completo",
            "completa",
            "completado",
            "completada"
        ]
    }

    for categoria, aliases in status_aliases.items():
        if status in aliases:
            return categoria

    return None

# ==========================================
# ADICIONAR TAREFA
# ==========================================


def adicionar_tarefa(
    nome_da_task: str,
    descricao_da_task: str,
    due_date: str,
    nome_quadro: str
):
    """Cria uma tarefa no quadro escolhido pelo usuário."""

    try:
        client = get_trello_client()

        meu_board = obter_quadro(client, nome_quadro)

        if not meu_board:
            return f"❌ Quadro '{nome_quadro}' não encontrado."

        listas = meu_board.list_lists()

        minha_lista = next(
            (
                lista for lista in listas
                if normalizar_texto(lista.name)
                in ["to do", "a fazer"]
            ),
            None
        )

        if not minha_lista:
            return (
                f"❌ Não encontrei a lista 'A Fazer' "
                f"ou 'To Do' no quadro '{nome_quadro}'."
            )

        data_formatada = formatar_data_trello(due_date)

        minha_lista.add_card(
            name=nome_da_task,
            desc=descricao_da_task,
            due=data_formatada
        )

        return (
            f"✅ Tarefa '{nome_da_task}' criada com sucesso "
            f"no quadro '{meu_board.name}'!"
        )

    except Exception as e:
        return (
            f"❌ Erro ao adicionar tarefa "
            f"'{nome_da_task}': {str(e)}"
        )



# ==========================================
# LISTAR TAREFAS
# ==========================================


def listar_tarefas(nome_quadro: str, status: str = "todas"):
    """Lista tarefas do quadro escolhido, com filtro por status."""

    try:
        client = get_trello_client()

        meu_board = obter_quadro(client, nome_quadro)

        if not meu_board:
            return f"❌ Quadro '{nome_quadro}' não encontrado."

        listas = meu_board.list_lists()

        status_normalizado = normalizar_texto(status)

        if status_normalizado in ["todas", "todos", "all"]:
            listas_filtradas = listas

        else:
            categoria = obter_categoria_status(status)

            if not categoria:
                return (
                    "❌ Status inválido. "
                    "Use: a fazer, em andamento ou concluído."
                )

            listas_filtradas = [
                lista for lista in listas
                if obter_categoria_status(lista.name) == categoria
            ]

        tarefas = []

        for lista in listas_filtradas:
            cards = lista.list_cards()

            for card in cards:
                tarefas.append({
                    "nome": card.name,
                    "descricao": card.desc,
                    "vencimento": card.due,
                    "status": lista.name,
                    "id": card.id,
                    "quadro": meu_board.name
                })

        if not tarefas:
            return (
                f"Nenhuma tarefa encontrada no quadro "
                f"'{meu_board.name}' para o status '{status}'."
            )

        return tarefas

    except Exception as e:
        return f"❌ Erro ao listar tarefas: {str(e)}"


# ==========================================
# MUDAR STATUS DA TAREFA
# ==========================================



def mudar_status_tarefa(
    nome_da_task: str,
    novo_status: str,
    nome_quadro: str,
    id_tarefa: str = ""
) -> str:
    """Move uma tarefa entre listas, tratando nomes duplicados."""

    try:
        client = get_trello_client()

        meu_board = obter_quadro(client, nome_quadro)

        if not meu_board:
            return f"❌ Quadro '{nome_quadro}' não encontrado."

        listas = meu_board.list_lists()

        categoria_destino = obter_categoria_status(novo_status)

        if not categoria_destino:
            return (
                "❌ Status inválido. "
                "Use: a fazer, em andamento ou concluído."
            )

        lista_destino = next(
            (
                lista for lista in listas
                if obter_categoria_status(lista.name) == categoria_destino
            ),
            None
        )

        if not lista_destino:
            return (
                f"❌ Não encontrei uma lista correspondente "
                f"ao status '{novo_status}'."
            )

        nome_normalizado = normalizar_texto(nome_da_task)

        tarefas_encontradas = []

        for lista in listas:
            for card in lista.list_cards():
                if normalizar_texto(card.name) == nome_normalizado:
                    tarefas_encontradas.append((card, lista))

        if not tarefas_encontradas:
            return (
                f"❌ Tarefa '{nome_da_task}' não encontrada "
                f"no quadro '{meu_board.name}'."
            )

        # Se o usuário informou um ID, localizar exatamente o card
        if id_tarefa:
            tarefas_encontradas = [
                (card, lista)
                for card, lista in tarefas_encontradas
                if str(card.id) == str(id_tarefa)
            ]

            if not tarefas_encontradas:
                return (
                    f"❌ Não encontrei a tarefa com o ID "
                    f"'{id_tarefa}' e nome '{nome_da_task}'."
                )

        # Evitar alterar uma tarefa errada quando existem duplicatas
        if len(tarefas_encontradas) > 1:
            opcoes = [
                (
                    f"- Lista: '{lista.name}' | "
                    f"ID: {card.id}"
                )
                for card, lista in tarefas_encontradas
            ]

            return (
                "⚠️ Encontrei mais de uma tarefa com esse nome. "
                "Informe qual deseja alterar utilizando o ID "
                "da tarefa:\n"
                + "\n".join(opcoes)
            )

        card_encontrado, lista_origem = tarefas_encontradas[0]

        if lista_origem.id == lista_destino.id:
            return (
                f"ℹ️ A tarefa '{card_encontrado.name}' já está "
                f"em '{lista_destino.name}'."
            )

        card_encontrado.change_list(lista_destino.id)

        return (
            f"✅ Tarefa '{card_encontrado.name}' movida com sucesso "
            f"no quadro '{meu_board.name}'! "
            f"{lista_origem.name} → {lista_destino.name}"
        )

    except Exception as e:
        return f"❌ Erro ao mudar status da tarefa: {str(e)}"

# ==========================================
# REMOVER TAREFA
# ==========================================

def remover_tarefa(
    nome_da_task: str,
    nome_quadro: str,
    confirmar: bool = False
) -> str:
    """Remove uma tarefa do quadro escolhido após confirmação."""

    try:
        client = get_trello_client()

        meu_board = obter_quadro(client, nome_quadro)

        if not meu_board:
            return f"❌ Quadro '{nome_quadro}' não encontrado."

        listas = meu_board.list_lists()

        nome_normalizado = normalizar_texto(nome_da_task)

        cards_encontrados = []

        for lista in listas:
            for card in lista.list_cards():
                if normalizar_texto(card.name) == nome_normalizado:
                    cards_encontrados.append((card, lista))

        if not cards_encontrados:
            return (
                f"❌ Tarefa '{nome_da_task}' não encontrada "
                f"no quadro '{meu_board.name}'."
            )

        if len(cards_encontrados) > 1:
            locais = [
                f"'{card.name}' na lista '{lista.name}'"
                for card, lista in cards_encontrados
            ]

            return (
                "⚠️ Encontrei mais de uma tarefa com esse nome. "
                "Informe qual deseja remover: "
                + "; ".join(locais)
            )

        card, lista = cards_encontrados[0]

        if not confirmar:
            return (
                f"⚠️ Confirma a exclusão da tarefa "
                f"'{card.name}' da lista '{lista.name}', "
                f"no quadro '{meu_board.name}'? "
                "Essa ação não poderá ser desfeita."
            )

        nome_card = card.name
        card.delete()

        return (
            f"✅ Tarefa '{nome_card}' removida com sucesso "
            f"do quadro '{meu_board.name}'!"
        )

    except Exception as e:
        return f"❌ Erro ao remover tarefa: {str(e)}"


# ==========================================
# CONFIGURAÇÃO DO AGENTE
# ==========================================

root_agent = Agent(
    model="gemini-3.5-flash",
    name="root_agent",
    description="Agente de Organização de Tarefas",

    instruction="""
    Você é um agente inteligente de organização de tarefas integrado ao Trello.

    Seu objetivo é ajudar o usuário a organizar, acompanhar e gerenciar suas tarefas através de uma conversa.

    REGRAS GERAIS:

    1. Sempre que o usuário iniciar uma solicitação de gerenciamento de tarefas sem informar um quadro, utilize listar_quadros para consultar os quadros disponíveis.

    2. Apresente os nomes dos quadros encontrados e pergunte em qual deles o usuário deseja trabalhar.

    3. Se o usuário já informar o nome do quadro, não precisa perguntar novamente. Consulte os quadros e valide se ele existe.

    4. Durante a conversa, mantenha o quadro escolhido como contexto para as próximas operações, até que o usuário escolha outro.

    5. Nunca invente nomes de quadros. Utilize somente os nomes retornados pelo Trello.

    6. Se o quadro informado não existir, apresente os quadros disponíveis e solicite outra escolha.

    FERRAMENTAS DISPONÍVEIS:

    1. listar_quadros:
    Consulta e apresenta todos os quadros disponíveis na conta Trello.

    2. adicionar_tarefa:
    Cria uma tarefa no quadro escolhido, utilizando nome, descrição e data de vencimento.

    3. listar_tarefas:
    Lista todas as tarefas ou filtra por status no quadro escolhido.

    4. mudar_status_tarefa:
    Move uma tarefa para outra lista no quadro escolhido.

    5. remover_tarefa:
    Remove uma tarefa do quadro escolhido, sempre solicitando confirmação explícita antes da exclusão.

    6. get_temporal_context:
    Obtém a data e hora atual para auxiliar na organização das tarefas.

    GERENCIAMENTO DE TAREFAS:

    - Ao criar uma tarefa, solicite nome, descrição e vencimento caso estejam faltando.
    - Utilize o quadro escolhido pelo usuário.
    - Ao listar tarefas, respeite o quadro e o filtro de status solicitado.
    - Ao mudar o status, aceite variações como concluído, concluido, concluída, done e finalizado.
    - Ao remover uma tarefa, apresente o nome e o quadro e aguarde uma confirmação explícita.
    - Se houver tarefas duplicadas ao alterar o status, apresente as opções com seus respectivos IDs e listas.
    - Solicite ao usuário que escolha a tarefa correta.
    - Utilize o parâmetro id_tarefa para alterar somente o card escolhido.
    - Nunca altere a primeira tarefa encontrada quando houver duplicidade.
    - Nunca exclua tarefas sem confirmação.
    - Sempre informe se a operação foi realizada com sucesso ou se ocorreu algum erro.

    ORGANIZAÇÃO DIÁRIA:

    Quando o usuário quiser organizar suas atividades do dia, utilize get_temporal_context para informar a data atual.

    Pergunte quais atividades ele deseja realizar e crie um card para cada tarefa no quadro escolhido.

    Continue perguntando se existem outras atividades até que o usuário informe que terminou.

    IMPORTANTE:

    Sempre utilize o nome do quadro escolhido nas chamadas das ferramentas.

    Não volte automaticamente para o quadro DIO depois que o usuário selecionar outro quadro.

    """,

    tools=[
        get_temporal_context,
        listar_quadros,
        adicionar_tarefa,
        listar_tarefas,
        mudar_status_tarefa,
        remover_tarefa
    ]
)
