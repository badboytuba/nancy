"""Set up the AI and its goals"""
from colorama import Fore, Style

from nancy import utils
from nancy.config.ai_config import AIConfig
from nancy.logs import logger


def prompt_user() -> AIConfig:
    """Prompt the user for input

    Returns:
        AIConfig: El objeto AIConfig que contiene la entrada del usuario.
    """
    ai_name = ""
    # Construct the prompt
    logger.typewriter_log(
        "¡Bienvenida a NAncy!",
        Fore.GREEN,
        "Le ayudaré en su búsqueda de información y proceso, haré todo lo posible para ofrecerle lo que desea.",
        speak_text=True,
    )

    logger.typewriter_log(
        "Crear un asistente de IA:",
        Fore.GREEN,
        "Introduce a continuación el nombre de tu IA y su función. Si no introduce nada, se cargará"
        " por defecto.",
        speak_text=True,
    )

    # Get AI Name from User
    logger.typewriter_log(
        "Ponle nombre a tu IA: ", Fore.GREEN, "Por ejemplo, 'BADER IA'"
    )
    ai_name = utils.clean_input("Nombre AI: ")
    if ai_name == "":
        ai_name = "BADER-IA"

    logger.typewriter_log(
        f"{ai_name} es!", Fore.LIGHTBLUE_EX, "Estoy a su servicio.", speak_text=True
    )

    # Get AI Role from User
    logger.typewriter_log(
        "Describa el papel de su IA: ",
        Fore.GREEN,
        "Por ejemplo, 'una IA diseñada para desarrollar y dirigir de forma autónoma empresas con"
        " el único objetivo de aumentar su patrimonio neto'",
    )
    ai_role = utils.clean_input(f"{ai_name} is: ")
    if ai_role == "":
        ai_role = "una IA diseñada para desarrollar y dirigir de forma autónoma empresas con"
        " el único objetivo de aumentar su patrimonio neto."

    # Enter up to 5 goals for the AI
    logger.typewriter_log(
        "Introduce hasta 5 objetivos para tu IA: ",
        Fore.GREEN,
        "For example: \nAumentar el patrimonio neto, Hacer crecer la cuenta de Twitter, Desarrollar y gestionar"
        " múltiples negocios de forma autónoma'",
    )
    print("No introduzca nada para cargar los valores por defecto, no introduzca nada cuando termine.", flush=True)
    ai_goals = []
    for i in range(5):
        ai_goal = utils.clean_input(f"{Fore.LIGHTBLUE_EX}Objetivo{Style.RESET_ALL} {i+1}: ")
        if ai_goal == "":
            break
        ai_goals.append(ai_goal)
    if not ai_goals:
        ai_goals = [
            "Aumentar el patrimonio neto",
            "Hacer crecer la cuenta de Twitter",
            "Desarrollar y gestionar múltiples negocios de forma autónoma",
        ]

    return AIConfig(ai_name, ai_role, ai_goals)
