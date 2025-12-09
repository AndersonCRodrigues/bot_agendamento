import logging
from datetime import datetime
from ..state import GraphState
from ...models import CustomerProfile, CompanyConfig

logger = logging.getLogger(__name__)


async def load_context_node(state: GraphState) -> GraphState:
    """
    Carrega os dados brutos do state inicial para objetos ricos.
    Transforma a Agenda JSON em texto legível para o Prompt.
    """
    try:
        logger.info(f"[LOAD_CONTEXT] Iniciando sessão {state['session_id']}")

        # 1. Hidrata os objetos Pydantic a partir dos dicts
        # (O main.py já vai passar os dados, aqui garantimos a tipagem)
        # Nota: state["company_config"] já deve ser um dict vindo do banco ou payload

        # 2. Formata a Agenda para o Prompt (String Legível)
        agenda_text = _format_agenda_text(state["company_agenda"])

        # 3. Formata o Contexto do Cliente para o Prompt
        customer_text = _format_customer_text(state["customer_profile"])

        return {
            **state,
            "rag_formatted": agenda_text,  # Reusando o campo 'rag_formatted' para a Agenda
            "customer_context_str": customer_text,  # Novo campo auxiliar se precisar
        }

    except Exception as e:
        logger.error(f"[LOAD_CONTEXT] Erro: {e}", exc_info=True)
        return {**state, "error": str(e)}


def _format_agenda_text(equipe_list: list) -> str:
    """Converte a lista de profissionais/slots em texto claro"""
    if not equipe_list:
        return "NENHUM HORÁRIO DISPONÍVEL NO MOMENTO."

    text = ""
    for prof in equipe_list:
        # prof é um dict (vinda do Pydantic .model_dump())
        text += f"\nProfissional: {prof['nome']} (ID: {prof['id']})\n"

        if not prof.get("agenda_disponivel"):
            text += "  - Sem horários livres.\n"
            continue

        for dia in prof["agenda_disponivel"]:
            text += f"  Data: {dia['data']}\n"
            slots_livres = [s for s in dia["slots"] if s["disponivel"]]

            if not slots_livres:
                text += "    (Lotado)\n"
            else:
                horarios = ", ".join([s["hora"] for s in slots_livres])
                text += f"    Horários: {horarios}\n"

        # Lista serviços para o bot saber o ID
        servicos = ", ".join([f"{s['nome']} (ID: {s['id']})" for s in prof["servicos"]])
        text += f"  Serviços: {servicos}\n"
        text += "-" * 20

    return text


def _format_customer_text(profile: CustomerProfile) -> str:
    return f"""
    Nome: {profile.nome or 'Não informado'}
    Telefone: {profile.telefone}
    Email: {profile.email or 'Não informado'}
    Status Cadastro: {'COMPLETO' if profile.is_data_complete else 'PENDENTE'}
    """
