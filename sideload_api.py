import bot_config
from utils.mind_data_manager import MindDataManager
from conversation_manager import ConversationManager
from app_logic import AppLogic

# Initialize managers and services
# These are global instances for the bot's lifecycle.
MIND_MANAGER = MindDataManager.get_instance()
CONVERSATION_MANAGER = ConversationManager(mind_manager=MIND_MANAGER)

# Token and allowed IDs are now fetched via bot_config functions
ALLOWED_USER_IDS = bot_config.get_allowed_user_ids()
ALLOWED_GROUP_IDS = bot_config.get_allowed_group_ids()

APPLICATION_LOGIC = AppLogic(
    conversation_manager=CONVERSATION_MANAGER,
    allowed_user_ids=ALLOWED_USER_IDS,
    allowed_group_ids=ALLOWED_GROUP_IDS
)

from utils.usage_accounting import set_fixed_model_for_round, set_quality_retries_for_round

def ask_sideload(
    message: str, 
    user_id: str | int = "api_user", 
    force_model: str | None = None,
    quality_retries: int | None = None
) -> tuple[str, str, str]:
    """
    Send a message to the sideload and get a response.
    
    Args:
        message (str): The message to send.
        user_id (str | int): Unique identifier for the conversation context. 
                             Defaults to "api_user".
        force_model (str | None): If provided, forces this model for the round.
        quality_retries (int | None): If provided, overrides the number of quality retries.
                                      0 means no retries (1 attempt).
    
    Returns:
        tuple[str, str, str]: (answer, provider_report, model_name)
    """
    
    # We use chat_type="API" to bypass Telegram ID checks
    # We cast user_id to int if possible, otherwise hash it or keep as is?
    # AppLogic expects user_id to be int in type hint, but handles str in logic mostly.
    # However, if we pass a string, conversation_key becomes that string.
    
    # process_user_request signature:
    # user_id: int, raw_user_message: str, chat_id: int, chat_type: str, generate_ai_reply: bool, ...
    
    if force_model:
        set_fixed_model_for_round(force_model)
    
    if quality_retries is not None:
        set_quality_retries_for_round(quality_retries)
    
    answer, provider_report, diag_info = APPLICATION_LOGIC.process_user_request(
        user_id=user_id, # type: ignore
        raw_user_message=message,
        chat_id=0, # Dummy chat ID
        chat_type="API",
        generate_ai_reply=True
    )
    
    model_name = "unknown_model"
    if diag_info and "models_used" in diag_info:
        models = list(diag_info["models_used"])
        if models:
            # If multiple models used (e.g. style/quality check), pick the first one or logic?
            # Usually the first one is the generator.
            # But let's join them or pick the first.
            model_name = models[0]
            # Clean up model name (remove provider prefix if present)
            if "/" in model_name:
                model_name = model_name.split("/")[-1]
    
    return answer if answer else "", provider_report or "", model_name

