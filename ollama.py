import ollama

response = ollama.generate(model='llama2', prompt='Why is the sky blue?')
print(response)
