"""Agent manager for managing GPT agents"""
from __future__ import annotations

from typing import Union

from nancy.config.config import Singleton
from nancy.llm_utils import create_chat_completion


class AgentManager(metaclass=Singleton):
    """Gerenciador de agentes para gerenciar agentes GPT"""

    def __init__(self):
        self.next_key = 0
        self.agents = {}  # key, (task, full_message_history, model)

    # Create new GPT agent
    # TODO: Centralise use of create_chat_completion() to globally enforce token limit

    def create_agent(self, task: str, prompt: str, model: str) -> tuple[int, str]:
        """Criar um novo agente e retornar sua chave

        Args:
            task: A tarefa a ser executada
            prompt: O prompt a ser usado
            model: O modelo a ser usado

        Returns:
            A chave do novo agente
        """
        messages = [
            {"role": "user", "content": prompt},
        ]

        # Start GPT instance
        agent_reply = create_chat_completion(
            model=model,
            messages=messages,
        )

        # Update full message history
        messages.append({"role": "assistant", "content": agent_reply})

        key = self.next_key
        # This is done instead of len(agents) to make keys unique even if agents
        # are deleted
        self.next_key += 1

        self.agents[key] = (task, messages, model)

        return key, agent_reply

    def message_agent(self, key: str | int, message: str) -> str:
        """Enviar uma mensagem a um agente e retornar sua resposta

        Args:
            key: A chave do agente para a mensagem
            message: A mensagem a ser enviada ao agente

        Returns:
            A resposta do agente
        """
        task, messages, model = self.agents[int(key)]

        # Add user message to message history before sending to agent
        messages.append({"role": "user", "content": message})

        # Start GPT instance
        agent_reply = create_chat_completion(
            model=model,
            messages=messages,
        )

        # Update full message history
        messages.append({"role": "assistant", "content": agent_reply})

        return agent_reply

    def list_agents(self) -> list[tuple[str | int, str]]:
        """Retorna uma lista de todos os agentes

        Returns:
            Uma lista de tuplas do formato (key, task)
        """

        # Return a list of agent keys and their tasks
        return [(key, task) for key, (task, _, _) in self.agents.items()]

    def delete_agent(self, key: Union[str, int]) -> bool:
        """Excluir um agente do gerenciador de agentes

        Args:
            key: A chave do agente a ser excluído

        Returns:
            Verdadeiro se for bem-sucedido, Falso caso contrário
        """

        try:
            del self.agents[int(key)]
            return True
        except KeyError:
            return False
