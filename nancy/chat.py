import time

from openai.error import RateLimitError

from nancy import token_counter
from nancy.config import Config
from nancy.llm_utils import create_chat_completion
from nancy.logs import logger

cfg = Config()


def create_chat_message(role, content):
    """
    Crie uma mensagem de bate-papo com a função e o conteúdo fornecidos.

    Args:
    role (str): A função do remetente da mensagem, por exemplo, "system", "user" ou "assistant".
    content (str): O conteúdo da mensagem.

    Returns:
    dict: Um dicionário que contém a função e o conteúdo da mensagem.
    """
    return {"role": role, "content": content}


def generate_context(prompt, relevant_memory, full_message_history, model):
    current_context = [
        create_chat_message("system", prompt),
        create_chat_message(
            "system", f"La fecha y hora actuales son{time.strftime('%c')}"
        ),
        create_chat_message(
            "system",
            f"Esto le recuerda los acontecimientos de su pasado:\n{relevant_memory}\n\n",
        ),
    ]

    # Add messages from the full message history until we reach the token limit
    next_message_to_add_index = len(full_message_history) - 1
    insertion_index = len(current_context)
    # Count the currently used tokens
    current_tokens_used = token_counter.count_message_tokens(current_context, model)
    return (
        next_message_to_add_index,
        current_tokens_used,
        insertion_index,
        current_context,
    )


# TODO: Change debug from hardcode to argument
def chat_with_ai(
    prompt, user_input, full_message_history, permanent_memory, token_limit
):
    """Interactúa con la API OpenAI, enviando el prompt, la entrada del usuario, el historial de mensajes,
    y la memoria permanente."""
    while True:
        try:
            """
            Interactuar con la API OpenAI, enviando el prompt, la entrada del usuario,
                historial de mensajes y memoria permanente.

            Args:
                prompt (str): El prompt que explica las reglas a la IA.
                user_input (str): La entrada del usuario.
                full_message_history (list): La lista de todos los mensajes enviados entre el
                    usuario y la IA.
                permanent_memory (Obj): El objeto de memoria que contiene la
                  permanente.
                token_limit (int): El número máximo de tokens permitidos en la llamada a la API.

            Returns:
            str: La respuesta de la IA.
            """
            model = cfg.fast_llm_model  # TODO: Change model from hardcode to argument
            # Reserve 1000 tokens for the response

            logger.debug(f"Token limit: {token_limit}")
            send_token_limit = token_limit - 1000

            relevant_memory = (
                ""
                if len(full_message_history) == 0
                else permanent_memory.get_relevant(str(full_message_history[-9:]), 10)
            )

            logger.debug(f"Memory Stats: {permanent_memory.get_stats()}")

            (
                next_message_to_add_index,
                current_tokens_used,
                insertion_index,
                current_context,
            ) = generate_context(prompt, relevant_memory, full_message_history, model)

            while current_tokens_used > 2500:
                # remove memories until we are under 2500 tokens
                relevant_memory = relevant_memory[:-1]
                (
                    next_message_to_add_index,
                    current_tokens_used,
                    insertion_index,
                    current_context,
                ) = generate_context(
                    prompt, relevant_memory, full_message_history, model
                )

            current_tokens_used += token_counter.count_message_tokens(
                [create_chat_message("user", user_input)], model
            )  # Account for user input (appended later)

            while next_message_to_add_index >= 0:
                # print (f"CURRENT TOKENS USED: {current_tokens_used}")
                message_to_add = full_message_history[next_message_to_add_index]

                tokens_to_add = token_counter.count_message_tokens(
                    [message_to_add], model
                )
                if current_tokens_used + tokens_to_add > send_token_limit:
                    break

                # Add the most recent message to the start of the current context,
                #  after the two system prompts.
                current_context.insert(
                    insertion_index, full_message_history[next_message_to_add_index]
                )

                # Count the currently used tokens
                current_tokens_used += tokens_to_add

                # Move to the next most recent message in the full message history
                next_message_to_add_index -= 1

            # Append user input, the length of this is accounted for above
            current_context.extend([create_chat_message("user", user_input)])

            # Calculate remaining tokens
            tokens_remaining = token_limit - current_tokens_used
            # assert tokens_remaining >= 0, "Tokens remaining is negative.
            # This should never happen, please submit a bug report at
            #  https://www.github.com/badboytuba/nancy"

            # Debug print the current context
            logger.debug(f"Token limit: {token_limit}")
            logger.debug(f"Send Token Count: {current_tokens_used}")
            logger.debug(f"Tokens remaining for response: {tokens_remaining}")
            logger.debug("------------ CONTEXT SENT TO AI ---------------")
            for message in current_context:
                # Skip printing the prompt
                if message["role"] == "system" and message["content"] == prompt:
                    continue
                logger.debug(f"{message['role'].capitalize()}: {message['content']}")
                logger.debug("")
            logger.debug("----------- END OF CONTEXT ----------------")

            # TODO: use a model defined elsewhere, so that model can contain
            # temperature and other settings we care about
            assistant_reply = create_chat_completion(
                model=model,
                messages=current_context,
                max_tokens=tokens_remaining,
            )

            # Update full message history
            full_message_history.append(create_chat_message("user", user_input))
            full_message_history.append(
                create_chat_message("assistant", assistant_reply)
            )

            return assistant_reply
        except RateLimitError:
            # TODO: When we switch to langchain, this is built in
            print("Error: ", "API Rate Limit Reached. Waiting 10 seconds...")
            time.sleep(10)
