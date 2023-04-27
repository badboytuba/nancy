from colorama import Fore, Style

from nancy.app import execute_command, get_command
from nancy.chat import chat_with_ai, create_chat_message
from nancy.config import Config
from nancy.json_utils.json_fix_llm import fix_json_using_multiple_techniques
from nancy.json_utils.utilities import validate_json
from nancy.logs import logger, print_assistant_thoughts
from nancy.speech import say_text
from nancy.spinner import Spinner
from nancy.utils import clean_input


class Agent:
    """Classe de agente para interagir com a Nancy.

    Attributes:
        ai_name: O nome do agente.
        memory: O objeto de memória a ser usado.
        full_message_history: O histórico completo da mensagem.
        next_action_count: O número de ações a serem executadas.
        system_prompt: O prompt do sistema é o prompt inicial que define tudo o que a IA precisa saber para realizar sua tarefa com êxito.
        Atualmente, as informações dinâmicas e personalizáveis no prompt do sistema são ai_name, description e goals.

        triggering_prompt: La última frase que verá la IA antes de responder. Para Nancy, esta frase es:
            Determina qué siguiente comando utilizar y responde utilizando el formato especificado anteriormente:
            El aviso de activación no forma parte del aviso del sistema porque entre el aviso del sistema y el aviso de activación
            pronto tenemos información contextual que puede distraer a la IA y hacer que se olvide de que su objetivo es encontrar la siguiente tarea a realizar.
            SYSTEM PROMPT
            CONTEXTUAL INFORMATION (memory, previous conversations, anything relevant)
            TRIGGERING PROMPT

        El aviso de activación recuerda a la IA su meta-tarea a corto plazo (definir la siguiente tarea)
    """

    def __init__(
        self,
        ai_name,
        memory,
        full_message_history,
        next_action_count,
        system_prompt,
        triggering_prompt,
    ):
        self.ai_name = ai_name
        self.memory = memory
        self.full_message_history = full_message_history
        self.next_action_count = next_action_count
        self.system_prompt = system_prompt
        self.triggering_prompt = triggering_prompt

    def start_interaction_loop(self):
        # Interaction Loop
        cfg = Config()
        loop_count = 0
        command_name = None
        arguments = None
        user_input = ""

        while True:
            # Discontinue if continuous limit is reached
            loop_count += 1
            if (
                cfg.continuous_mode
                and cfg.continuous_limit > 0
                and loop_count > cfg.continuous_limit
            ):
                logger.typewriter_log(
                    "Continuous Limit Reached: ", Fore.YELLOW, f"{cfg.continuous_limit}"
                )
                break

            # Send message to AI, get response
            with Spinner("Pensando... "):
                assistant_reply = chat_with_ai(
                    self.system_prompt,
                    self.triggering_prompt,
                    self.full_message_history,
                    self.memory,
                    cfg.fast_token_limit,
                )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument

            assistant_reply_json = fix_json_using_multiple_techniques(assistant_reply)

            # Print Assistant thoughts
            if assistant_reply_json != {}:
                validate_json(assistant_reply_json, "llm_response_format_1")
                # Get command name and arguments
                try:
                    print_assistant_thoughts(self.ai_name, assistant_reply_json)
                    command_name, arguments = get_command(assistant_reply_json)
                    # command_name, arguments = assistant_reply_json_valid["command"]["name"], assistant_reply_json_valid["command"]["args"]
                    if cfg.speak_mode:
                        say_text(f"Quiero ejecutar {command_name}")
                except Exception as e:
                    logger.error("Error: \n", str(e))

            if not cfg.continuous_mode and self.next_action_count == 0:
                ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
                # Get key press: Prompt the user to press enter to continue or escape
                # to exit
                logger.typewriter_log(
                    "PRÓXIMA ACCIÓN: ",
                    Fore.CYAN,
                    f"COMMANDO = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
                    f"ARGUMENTOS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                )
                print(
                    "Enter 'y' to authorise command, 'y -N' to run N continuous "
                    "commands, 'n' to exit program, or enter feedback for "
                    f"{self.ai_name}...",
                    flush=True,
                )
                while True:
                    console_input = clean_input(
                        Fore.MAGENTA + "Input:" + Style.RESET_ALL
                    )
                    if console_input.lower().strip() == "y":
                        user_input = "GENERATE NEXT COMMAND JSON"
                        break
                    elif console_input.lower().strip() == "":
                        print("Invalid input format.")
                        continue
                    elif console_input.lower().startswith("y -"):
                        try:
                            self.next_action_count = abs(
                                int(console_input.split(" ")[1])
                            )
                            user_input = "GENERATE NEXT COMMAND JSON"
                        except ValueError:
                            print(
                                "Invalid input format. Please enter 'y -n' where n is"
                                " the number of continuous tasks."
                            )
                            continue
                        break
                    elif console_input.lower() == "n":
                        user_input = "EXIT"
                        break
                    else:
                        user_input = console_input
                        command_name = "human_feedback"
                        break

                if user_input == "GENERATE NEXT COMMAND JSON":
                    logger.typewriter_log(
                        "-=-=-=-=-=-=-= COMANDO AUTORIZADO POR EL USUARIO-=-=-=-=-=-=-=",
                        Fore.MAGENTA,
                        "",
                    )
                elif user_input == "EXIT":
                    print("Exiting...", flush=True)
                    break
            else:
                # Print command
                logger.typewriter_log(
                    "PRÓXIMA ACCIÓN: ",
                    Fore.CYAN,
                    f"COMMANDO = {Fore.CYAN}{command_name}{Style.RESET_ALL}"
                    f"  ARGUMENTOS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                )

            # Execute command
            if command_name is not None and command_name.lower().startswith("error"):
                result = (
                    f"Commando {command_name} arrojó el siguiente error: {arguments}"
                )
            elif command_name == "human_feedback":
                result = f"Reacción humana:: {user_input}"
            else:
                result = (
                    f"Commando {command_name} devuelto: "
                    f"{execute_command(command_name, arguments)}"
                )
                if self.next_action_count > 0:
                    self.next_action_count -= 1

            memory_to_add = (
                f"Respuesta del asistente: {assistant_reply} "
                f"\nResultado: {result} "
                f"\nReacción humana:{user_input} "
            )

            self.memory.add(memory_to_add)

            # Check if there's a result from the command append it to the message
            # history
            if result is not None:
                self.full_message_history.append(create_chat_message("system", result))
                logger.typewriter_log("SISTEMA: ", Fore.YELLOW, result)
            else:
                self.full_message_history.append(
                    create_chat_message("system", "Unable to execute command")
                )
                logger.typewriter_log(
                    "SISTEMA: ", Fore.YELLOW, "Unable to execute command"
                )
