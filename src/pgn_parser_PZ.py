import re
import os
import pandas as pd

MODEL_DIR = {
    "Deepseek-Alpha": './Deepseek-Alpha/',
    "Gemini_2.5_Pro": './Gemini_2.5_Pro/',
    "GPT-4o": './GPT-4o/',
    "Grok-3": './Grok-3/',
    "Llama-4-Maverick": './Llama-4-Maverick/',
}
PUZZLE_CSV = "puzzles_PGN.csv"
OUTPUT_CSV = 'parsed_output.csv'
PROMPT_DIR = ['../Prompt_A/puzzle_test/', '../Prompt_B/puzzle_test/']

def main():
    print(f"--- LLM response Parser ---")
    # Load puzzle datasets
    puzzles = pd.read_csv(PUZZLE_CSV)

    # Iterate through all puzzles & models
    for prompt_dir in PROMPT_DIR:
        for model_name in MODEL_DIR.keys():
            raw_data_files = os.listdir(prompt_dir + MODEL_DIR[model_name])
            result = {'N': [], 'fen': [], 'llm_output': [], 'correct_pgn': []}

            for index, row in puzzles.iterrows():
                fen = row['FEN']
                mate_in_n = row['Mate in N']
                solution = row['Solution PGN']

                with open(prompt_dir + MODEL_DIR[model_name] + raw_data_files[index], "r", encoding="utf-8") as raw_text_wrapper:
                    raw_text = raw_text_wrapper.read()
                    llm_pgn = re.search(r'\[FINAL PGN\](.*)', raw_text, re.DOTALL)
                    if llm_pgn == None:
                        llm_pgn = re.search(r'--- FINAL PGN ---(.*)', raw_text, re.DOTALL)
                        if llm_pgn == None:
                            llm_pgn = 'ERROR'
                            print(f'{raw_data_files[index]}: {llm_pgn}')
                        else:
                            llm_pgn = llm_pgn.group(1).strip().replace('[FINAL PGN]', '').strip()
                            llm_pgn = llm_pgn[llm_pgn.find('1.'):]
                            llm_pgn = llm_pgn.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                            print(f'{raw_data_files[index]}: {llm_pgn}')
                    else: 
                        llm_pgn = llm_pgn.group(1).strip().replace('[FINAL PGN]', '').strip()
                        llm_pgn = llm_pgn[llm_pgn.find('1.'):]
                        llm_pgn = llm_pgn.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                        print(f'{raw_data_files[index]}: {llm_pgn}')

                    if llm_pgn.strip() == '':
                        llm_pgn = 'ERROR'
                    result['N'].append(mate_in_n)
                    result['fen'].append(fen)
                    result['llm_output'].append(llm_pgn)
                    result['correct_pgn'].append(solution)
            df = pd.DataFrame(result)   
            df.to_csv(prompt_dir + MODEL_DIR[model_name] + OUTPUT_CSV, index=False)
            
            print(f'File saved: {OUTPUT_CSV}')


    print("Process complete.")

if __name__ == "__main__":
    main()