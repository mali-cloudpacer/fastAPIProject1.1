import re
import textwrap


def format_llm_response(llm_response: str, line_width: int = 80) -> str:
    """
    Formats the LLM response to make it visually better for chat display.

    Parameters:
    - llm_response (str): The response from the LLM.
    - line_width (int): The maximum width of each line for wrapping.

    Returns:
    - str: The formatted response.
    """
    # Remove newlines and extra whitespace
    if llm_response is None:
        llm_response = 'LLM failed to generate response due to lengthy data but you can view the query/results'
    formatted_response = re.sub(r'\s+', ' ', llm_response.strip())

    # Wrap the text to the desired line width
    wrapped_response = textwrap.fill(formatted_response, width=line_width)
    wrapped_response = wrapped_response.replace('\n', ' ').strip()

    return wrapped_response