import os
import pandas as pd
from openai import AzureOpenAI
from google import genai

# --- ENVIRONMENT SETUP ---

ROLE_PROMPT = """
You are a professional chess engine. Answer the following chess-related question.
"""
PUZZLE_TEMPLETE_A = """
Analyze the following chess puzzle and provide your thought process before outputting the final PGN solution.

The current position is defined by the FEN: **{fen}**
The goal is to find a forced checkmate in **{mate_in_n}** moves (Mate in {mate_in_n}).

--- THOUGHT PROCESS START ---
Analyze the required depth, the key candidate moves, and the opponent's forced responses, ensuring every move in the sequence is legal and leads to the target checkmate.

--- FINAL OUTPUT INSTRUCTIONS ---
1. Provide the PGN move sequence ONLY after the "[FINAL PGN]" tag.
2. Add white and black move numbers appropriately.
3. Must include all notations for special moves (e.g., + for check, # for checkmate).
4. Do not include anything else than PGN after "[FINAL PGN]" tag.

[FINAL PGN]

"""
PUZZLE_TEMPLETE_B = """
Your task is to analyze the following position and find a forced checkmate in exactly {mate_in_n} moves for the side to move.

The current position is given in FEN: {fen}
The objective is: mate in {mate_in_n} moves (no faster, no slower).
Before answering, write out a clear step-by-step reasoning process. Do not jump directly to the final move without this reasoning.

--- THOUGHT PROCESS START ---
1. Identify which side is to move and the king you must checkmate.
2. List the most promising candidate moves for the attacking side.
3. For each candidate, calculate a concrete line for exactly {mate_in_n} moves, assuming the opponent plays reasonable defensive moves.
4. At each step, explicitly verify that:
   - every move is legal,
   - checkmate is delivered on the final move,
   - there is no earlier checkmate before move {mate_in_n}.
Conclude by choosing the best forced line.

--- FINAL OUTPUT INSTRUCTIONS ---
1. After the tag "[FINAL PGN]", output only the final move sequence in PGN-style notation.
2. Include move numbers for both White and Black (e.g., "1. Qh5+ Kf8 2. Qf7#").
3. Use standard symbols: "+" for check, "#" for checkmate, "O-O"/"O-O-O" for castling, etc.
4. Do not output any explanations, comments, or alternative lines after "[FINAL PGN]".

[FINAL PGN]

"""
LEGALITY_TEMPLETE_A = """
Analyze the following chess positions and provide your thought process before outputting the final PGN solution.

The current position is defined by the FEN: **{fen}**
The goal is to find one legal move that can be made in this position.

--- THOUGHT PROCESS START ---
Analyze all moveable pieces. Only consider your moves, not opponent's moves. Only consider moves that can be made for this turn.

--- FINAL OUTPUT INSTRUCTIONS ---
1. Provide the PGN move sequence ONLY after the "[FINAL PGN]" tag.
2. Add white and black move numbers appropriately.
3. Must include all notations for special moves (e.g., + for check, # for checkmate).
4. Do not include anything else than PGN after "[FINAL PGN]" tag.
5. Do not use any other notation than PGN.

[FINAL PGN]
"""
LEGALITY_TEMPLETE_B = """
Choose a single legal move for the side to move in a given position.

You will be given a chess position in FEN format: {fen}
Your task is to output exactly one legal move that can be played from this position by the side to move.
Before answering, write out a clear step-by-step reasoning process. Do not jump directly to the final move without this reasoning.

--- THOUGHT PROCESS START ---

Determine which side is to move (White or Black).
Briefly consider which of that side’s pieces can move.
For a few candidate moves, mentally check:
the move follows the piece’s movement rules,
it does not leave your own king in check,
it does not move onto a square already occupied by your own piece.
Then pick one legal move.

--- FINAL OUTPUT INSTRUCTIONS ---

After the tag "[FINAL PGN]", output only a single move in PGN/long algebraic notation (e.g., "Qh5+", "O-O", "exd5").
Include move numbers for both White and Black (e.g., "1. Qh5+").
Do not output multiple moves or a sequence; only the move you choose for this turn.
Do not include any explanations, comments, or alternative moves after "[FINAL PGN]".
Do not use any notation other than standard chess move notation.

[FINAL PGN]
"""

# All API keys and Endpoint URL are deleted for privacy reason
API_KEYS_ENDPOINT = {
    "OPENAI": (
        "<API KEY HERE>", 
        "<ENDPOINT URL HERE>"
    ),
    "GEMINI": (
        "<API KEY HERE>",
        ""
    ),
    "GROK": (
        "<API KEY HERE>",
        "<ENDPOINT URL HERE>"
    ),
    "DEEPSEEK": (
        "<API KEY HERE>",
        "<ENDPOINT URL HERE>"
    ),
    "LLAMA": (
        "<API KEY HERE>",
        "<ENDPOINT URL HERE>"
    )
}

MODEL_MAP = {
    "GPT-4o": ("OPENAI", "gpt-4o"),
    "Gemini_2.5_Pro": ("GEMINI", "gemini-2.5-pro"),
    "Grok-3": ("GROK", "grok-3"),
    "Deepseek-Alpha": ("OPENAI", "deepseek-alpha"),
    "Llama-4-Maverick": ("LLAMA", "Llama-4-Maverick-17B-128E-Instruct-FP8"),
}
PUZZLE_CSV = "puzzles_PGN.csv"

# --- API Client setup ---
def get_api_client(api_type: str):
    """
    Return appropirate API client according to the input
    
    Args:
        api_type: The name of the client to be return

    Returns:
        Appropirate LLM API client
    """
    key, endpoint = API_KEYS_ENDPOINT.get(api_type)
    
    if api_type == "OPENAI":
        return AzureOpenAI(api_version='2025-01-01-preview', azure_endpoint=endpoint, api_key=key)
    elif api_type == "GEMINI":
        return genai.Client(api_key=key)
    elif api_type == "GROK":
        return AzureOpenAI(api_version='2024-05-01-preview', azure_endpoint=endpoint, api_key=key)
    elif api_type == "DEEPSEEK":
        return AzureOpenAI(api_version='2024-05-01-preview', azure_endpoint=endpoint, api_key=key)
    elif api_type == "LLAMA":
        return AzureOpenAI(api_version='2024-05-01-preview', azure_endpoint=endpoint, api_key=key)
    else:
        raise ValueError(f"Unknown API type: {api_type}")

# --- LLM API call function ---
def solve_puzzle_with_llm(model_name: str, prompt: str) -> str:
    """
    Call appropirate LLM API according to model's name.

    Args:
        model_name: name of the model
        fen: the puzzle's FEN
        mate_in_n: the puzzle's n value

    Returns:
        Model's raw response (only text)
    """
    api_type, model_name = MODEL_MAP[model_name]
    try:
        client = get_api_client(api_type)
        
        if api_type == "OPENAI":
            response = client.chat.completions.create(
                model = model_name,
                messages = [
                    {"role": "system", "content": ROLE_PROMPT}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
                )
            if response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return "API_ERROR: No content in response"
        
        elif api_type == "GEMINI":
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction = ROLE_PROMPT,
                    temperature = 0.0
                    )
            )
            return response.text
        
        elif api_type == "GROK":
            response = client.chat.completions.create(
                model = model_name,
                messages = [
                    {"role": "system", "content": ROLE_PROMPT}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
                )
            if response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return "API_ERROR: No content in response"
            
        elif api_type == "DEEPSEEK":
            response = client.chat.completions.create(
                model = model_name,
                messages = [
                    {"role": "system", "content": ROLE_PROMPT}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
                )
            if response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return "API_ERROR: No content in response"
            
        elif api_type == "LLAMA":
            response = client.chat.completions.create(
                model = model_name,
                messages = [
                    {"role": "system", "content": ROLE_PROMPT}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
                )
            if response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                return "API_ERROR: No content in response"
            
        else:
            return f"API_TYPE_NOT_IMPLEMENTED"

    except Exception as e:
        print(f"An API error occurred on {model_name}")
        return f"API_ERROR: {str(e)[:100]}"

# --- Main execution logic ---
def main():
    print(f"--- Starting Multi-LLM Chess Puzzle Solver ---")
    
    # Load puzzle datasets
    puzzles = pd.read_csv(PUZZLE_CSV)
    # Iterate through all puzzles & models
    for mode in ['legal_moves', 'puzzle_test']:                  
        for model_name in MODEL_MAP.keys():
            for index, row in puzzles.iterrows():
                prompts_set = {}
                if mode == 'legal_moves':
                    prompts_set = {'Prompt_A': LEGALITY_TEMPLETE_A, 'Prompt_B': LEGALITY_TEMPLETE_B}
                else:
                    prompts_set = {'Prompt_A': PUZZLE_TEMPLETE_A ,'Prompt_B':  PUZZLE_TEMPLETE_B}

                for prompt_type in prompts_set.keys():
                    prompt = ''
                    fen = row['FEN']
                    mate_in_n = row['Mate in N']
                    if mode == 'legal_moves':
                        prompt = prompts_set[prompt_type].format(fen=fen)
                    else:
                        prompt = prompts_set[prompt_type].format(fen=fen, mate_in_n=mate_in_n)
                    
                    print(f"\nProcessing {mode} with {prompt_type} {index + 1}/{len(puzzles)}")
                    print(f"-> Calling {model_name}...")
                    llm_raw_response = solve_puzzle_with_llm(model_name, prompt)
                    
                    # Assert when Error occured, or parse result if successfully returned response
                    if llm_raw_response.startswith("API_ERROR"):
                        print(llm_raw_response)
                        print(f"   {model_name} Result: API ERROR")
                        assert False, "Skipping further processing due to API error."
                    else:
                        # Save raw output into txt file
                        os.makedirs(f"../{prompt_type}/{mode}/{model_name}", exist_ok=True)
                        file_path = f"../{prompt_type}/{mode}/{model_name}/output_{"{:02d}".format(index + 1)}.txt"
                        file_object = open(file_path, 'w', encoding='utf-8')
                        file_object.write(llm_raw_response)
                        file_object.close()
                        print(f"Data saved: {file_path}")
        print("Process complete.")

if __name__ == "__main__":
    main()