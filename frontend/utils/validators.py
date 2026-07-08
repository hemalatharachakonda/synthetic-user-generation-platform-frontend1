"""Simple input validation helpers for form pages."""


def validate_experiment_form(product_name: str, description: str,
                              target_audience: str, objectives: str) -> list[str]:
    """Returns a list of error messages. Empty list means valid."""
    errors = []
    if not product_name or not product_name.strip():
        errors.append("Product name is required.")
    elif len(product_name.strip()) < 2:
        errors.append("Product name is too short.")

    if not description or len(description.strip()) < 10:
        errors.append("Please provide a product description (10+ characters).")

    if not target_audience or len(target_audience.strip()) < 5:
        errors.append("Please describe your target audience (5+ characters).")

    if not objectives or len(objectives.strip()) < 5:
        errors.append("Please describe your research objectives (5+ characters).")

    return errors


def validate_persona_count(count: int, min_count: int, max_count: int) -> list[str]:
    errors = []
    if count < min_count or count > max_count:
        errors.append(f"Persona count must be between {min_count} and {max_count}.")
    return errors


def validate_chat_message(message: str) -> list[str]:
    errors = []
    if not message or not message.strip():
        errors.append("Message cannot be empty.")
    return errors
