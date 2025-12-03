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
PROMPT_DIR = ['../Prompt_A/puzzle_test/', '../Prompt_B/puzzle_test/']

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

def analyze_constraint_sacrifice(raw_pgn: str, initial_fen: str, mate_in_n: int, correct_pgn: str) -> dict:
    """
    Analysis output and determine the error
    
    Args:
        raw_pgn: Parsed PGN created by LLM
        initial_fen: The initial state of the board
        mate_in_n: Required logical depth
        
    Returns:
        dict: Analysis result
    """
    results = {
        "is_solved": 0,
        "error": 0,
        "CAV": 0,
        "NCV": 0,
        "PMV": 0
    }
    try:
        board = chess.Board(initial_fen)
        initial_turn = board.turn
        moves_san = parse_pgn_to_san_list(raw_pgn) 
        
    except Exception as e:
        print(f"Error parsing PGN or FEN: {e}")
        return results

    # --- CAV ---
    if len(raw_pgn[raw_pgn.find('1.'):raw_pgn.find(' ')]) != len(correct_pgn[correct_pgn.find('1.'):correct_pgn.find(' ')]):
        results["CAV"] = 1

    # --- NCV ---
    else:
        for i in range(1, 5):
            if raw_pgn.find(f'{i}.') != -1 and correct_pgn.find(f'{i}.') != -1:
                continue
            elif raw_pgn.find(f'{i}.') == -1 and correct_pgn.find(f'{i}.') == -1:
                break
            else:
                results['NCV'] = 1

    # --- PMV ---
    for i, san_move in enumerate(moves_san):
        try: 
            move = board.parse_san(san_move)
        except Exception:
            results["PMV"] = 1
            return results 
        
        # Apply the move if the move is legal
        board.push_san(san_move)
    
    # Check if checkmated
    if board.is_checkmate():
        # If the initial player got mated, then CAV
        if board.turn != initial_turn:
            results["CAV"] = 0
            results["is_solved"] = 1
        else:
            results["CAV"] = 1 
            results["is_solved"] = 0
            
    return results

if __name__ == '__main__':
    # Run analysis function iterating through all data
    for prompt in PROMPT_DIR:
        for model_name in MODEL_DIR.keys():
            df = pd.read_csv(prompt + MODEL_DIR[model_name] + INPUT_CSV)
            sol_df = pd.read_csv(PUZZLE_CSV)
            print(f"Reading {model_name}'s {INPUT_CSV} and analysis Constraint Sacrifice.")

            analysis_results: List[Dict[str, Any]] = []
            for index, row in df.iterrows():
                mate_in_n = row['N']
                initial_fen = row['fen']
                raw_pgn = row['llm_output']
                correct_pgn = row['correct_pgn']
                
                # If LLM error, return error
                if raw_pgn.strip() == 'ERROR':
                        results = {
                            "is_solved": 0,
                            "error": 1,
                            "CAV": 0,
                            "NCV": 0,
                            "PMV": 0
                        }
                else:
                    results = analyze_constraint_sacrifice(
                        raw_pgn=raw_pgn,
                        initial_fen=initial_fen,
                        mate_in_n=mate_in_n,
                        correct_pgn=correct_pgn
                    )
                
                # Combine with original data
                results['N'] = mate_in_n
                analysis_results.append(results)

            # Save results into CSV form
            results_df = pd.DataFrame(analysis_results)
            results_df.to_csv(prompt + OUTPUT_CSV.format(model_name=model_name), index=False)
        
            print(f"Saved: {OUTPUT_CSV.format(model_name=model_name)}.")

    print(f"Analysis complete.")