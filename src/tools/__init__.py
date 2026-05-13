"""Tools do agente Consignado — exporta todas as funções para facilitar importação.

Cada tool é decorada com @tool do Strands e exposta via AgentCore Gateway (MCP).
"""

from __future__ import annotations

from tools.biometry import accept_proposal, continue_biometry, start_biometry
from tools.consent_term import accept_consent_term, create_consent_term
from tools.proposal import create_proposal
from tools.simulation import create_simulation, get_simulations

__all__ = [
    "create_consent_term",
    "accept_consent_term",
    "create_simulation",
    "get_simulations",
    "create_proposal",
    "start_biometry",
    "continue_biometry",
    "accept_proposal",
]
