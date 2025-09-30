none_summary_prompt = """Generate a summary of the conversation until the present moment.
Always conserve entities from the text (values, dates, names, products, etc.) in the summary.
Be concise and objective"""

def existing_summary_prompt(summary: str):
    return f"""This is the summary of the conversation until the present moment:\n{summary}\n\n
Remake the summary taking into account the most recent messages above.
Conserve entities from the text (values, dates, names, products, etc.).
Be concise and objective."""