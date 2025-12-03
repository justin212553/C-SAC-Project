import chess
import re
import pandas as pd
from typing import List, Dict, Any

MODEL_DIR = {
    "Deepseek-Alpha": './Deepseek-Alpha/',
    "Gemini_2.5_Pro": './Gemini_2.5_Pro/',
    "GPT-4o": './GPT-4o/',
    "Grok-3": './Grok-3/',
    "Llama-4-Maverick": './Llama-4-Maverick/',
}
INPUT_CSV = 'parsed_output.csv'
OUTPUT_CSV = 'results_{model_name}.csv'
PUZZLE_CSV = "puzzles_PGN.csv"
PROMPT_DIR = ['../Prompt_A/legal_moves/', '../Prompt_B/legal_moves/']

def parse_pgn_to_san_list(raw_pgn: str) -> List[str]:
    """
    Parse PGN into list of moves

    Args:
        raw_pgn: Parsed PGN created by LLM
    Returns:
        dict: Parsed result
    """
    # Delete all numbers and unexpected characters
    pgn_text = raw_pgn.strip()
    pgn_text = re.sub(r'\s*\([^)]*\)', '', pgn_text).strip()
    pgn_text = re.sub(r'(1-0|0-1|1/2-1/2)', '', pgn_text)
    pgn_text = re.sub(r'\s*\d+\s*(\.|\.\.)\s*', ' ', pgn_text).strip()
    pgn_text = pgn_text.replace('.', '')
    
    # Separate tokens with a space
    moves = [token.strip() for token in pgn_text.split() if token.strip()]

    return moves

def analyze_constraint_sacrifice(raw_pgn: str, initial_fen: str) -> dict:
    """
    Analysis output and determine the error
    
    Args:
        raw_pgn: Parsed PGN created by LLM
        initial_fen: The initial state of the board
        
    Returns:
        dict: Analysis result
    """
    results = {
        'error': 0,
        'legal': 1
    }

    board = chess.Board(initial_fen)

    # Check if move is valid
    moves_san = parse_pgn_to_san_list(raw_pgn) 
    try: 
        move = board.parse_san(moves_san[0])
        return results
    except Exception:
        results["legal"] = 0
        return results 


if __name__ == '__main__':
    # Run analysis function iterating through all data
    for prompt in PROMPT_DIR:
        for model_name in MODEL_DIR.keys():
            df = pd.read_csv(prompt + MODEL_DIR[model_name] + INPUT_CSV)
            sol_df = pd.read_csv(PUZZLE_CSV)
            print(f"Reading {INPUT_CSV} and analysis Legal Move Count.")

            analysis_results: List[Dict[str, Any]] = []
            for index, row in df.iterrows():
                
                initial_fen = row['fen']
                raw_pgn = row['llm_output']
                
                # If LLM error, return error
                if raw_pgn.strip() == 'ERROR':
                            results = {
                                'error': 1,
                                'legal': 0
                            }
                else:
                    results = analyze_constraint_sacrifice(
                        raw_pgn=raw_pgn,
                        initial_fen=initial_fen,
                    )
                analysis_results.append(results)

            # Save results into CSV form
            results_df = pd.DataFrame(analysis_results)
            results_df.to_csv(prompt + OUTPUT_CSV.format(model_name=model_name), index=False)
        
            print(f"Saved:{OUTPUT_CSV.format(model_name=model_name)}.")

    print(f"Analysis complete.")