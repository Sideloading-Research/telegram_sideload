from ai_providers.rate_limited_ai_wrapper import (
    PROVIDER_FROM_ENV,  # Default provider if not overridden
    ask_gpt_multi_message,
)
from bot_config import get_provider_indicators, GLOBAL_ENABLE_USER_DEFINED_AI_PROVIDERS7

# Module-level state for the currently selected provider for a given interaction.
# This might be better managed per-user or per-chat in a more complex scenario,
# but for now, mirroring the existing global SELECTED_PROVIDER behavior.
_selected_provider_for_current_call = None

def update_provider_from_user_input(user_input):
    """ 
    Checks if the user input starts with a provider indicator.
    If so, updates the _selected_provider_for_current_call for the current interaction.
    Returns a tuple: (bool: if_provider_switched, str: report_message).
    """
    if not GLOBAL_ENABLE_USER_DEFINED_AI_PROVIDERS7:
        return False, ""
    
    global _selected_provider_for_current_call
    current_default_provider = _selected_provider_for_current_call or PROVIDER_FROM_ENV

    provider_indicators = get_provider_indicators()
    for provider_name, indicators in provider_indicators.items():
        for indicator in indicators:
            if user_input.lower().startswith(indicator):
                if provider_name != _selected_provider_for_current_call:
                    report = f"Provider switched: {current_default_provider} -> {provider_name}"
                    print(report)
                    _selected_provider_for_current_call = provider_name
                    return True, report
                else:
                    # Provider indicated is already the selected one, no actual switch
                    _selected_provider_for_current_call = provider_name # Ensure it's set if it was None
                    return False, f"Provider confirmed: {provider_name}"
    
    # If no indicator matched, but a provider was previously selected for this call, keep it.
    # If no indicator matched and no provider was set for this call, it will default to PROVIDER_FROM_ENV in get_ai_response.
    return False, "" # No switch occurred based on this specific input

def get_ai_response(messages_history, user_input_for_provider_selection, max_length=500):
    """
    Gets a response from the AI provider.
    Determines the provider based on user input or defaults.
    `user_input_for_provider_selection` is the raw user message text used to check for provider indicators.
    """
    global _selected_provider_for_current_call
    
    # Reset _selected_provider_for_current_call for this call cycle before checking. 
    # This ensures that a previous call's selection doesn't unintentionally carry over 
    # if the current user_input doesn't specify a provider.
    previous_selection = _selected_provider_for_current_call
    _selected_provider_for_current_call = None 

    switched, report = update_provider_from_user_input(user_input_for_provider_selection)
    
    provider_to_use = _selected_provider_for_current_call or PROVIDER_FROM_ENV

    # If no switch happened but there was a previous selection for the *user session* (not this specific call cycle prior to reset),
    # and no new selection was made, this logic might need refinement if SELECTED_PROVIDER was meant to be more sticky across calls
    # without being re-indicated. The original logic with global SELECTED_PROVIDER implied stickiness.
    # For now, this interprets it as: check input, if indicator use it, else use default from env.
    # If stickiness across multiple messages from the same user *without re-indicating* is desired,
    # _selected_provider_for_current_call would need to be managed at a higher scope (e.g., per user session in ConversationManager)

    print(f"Using AI provider: {provider_to_use}")
    
    answer = ask_gpt_multi_message(
        messages_history,
        max_length=max_length,
        user_defined_provider=provider_to_use, # Pass the determined provider
    )
    return answer, report # also return the switch report if any 