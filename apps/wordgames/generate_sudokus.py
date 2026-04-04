"""
Generate valid 6x6 sudoku puzzles (2x3 boxes) and write them to data/sudokus/*.json
Each language gets the same puzzles since sudoku is language-independent.
Difficulties: easy (>=24 givens), medium (18-23), hard (12-17)
"""
import json, random, copy, sys
from pathlib import Path

LANGS = ["en", "tr", "nl", "id", "ms"]
BASE = Path(__file__).parent / "data" / "sudokus"
SIZE = 6
BOX_ROWS = 2
BOX_COLS = 3
SYMBOLS = [str(i) for i in range(1, SIZE + 1)]


def is_valid(board, row, col, num):
    # row
    if num in board[row]:
        return False
    # col
    if num in [board[r][col] for r in range(SIZE)]:
        return False
    # box
    br = (row // BOX_ROWS) * BOX_ROWS
    bc = (col // BOX_COLS) * BOX_COLS
    for r in range(br, br + BOX_ROWS):
        for c in range(bc, bc + BOX_COLS):
            if board[r][c] == num:
                return False
    return True


def solve(board):
    for row in range(SIZE):
        for col in range(SIZE):
            if board[row][col] == "":
                nums = SYMBOLS[:]
                random.shuffle(nums)
                for num in nums:
                    if is_valid(board, row, col, num):
                        board[row][col] = num
                        if solve(board):
                            return True
                        board[row][col] = ""
                return False
    return True


def generate_solution():
    board = [["" for _ in range(SIZE)] for _ in range(SIZE)]
    solve(board)
    return board


def make_puzzle(solution, num_givens):
    givens = copy.deepcopy(solution)
    positions = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    random.shuffle(positions)
    remove_count = SIZE * SIZE - num_givens
    removed = 0
    for r, c in positions:
        if removed >= remove_count:
            break
        givens[r][c] = ""
        removed += 1
    return givens


def verify_puzzle(solution):
    """Double-check solution validity."""
    valid_set = set(SYMBOLS)
    # rows
    for row in solution:
        if set(row) != valid_set:
            return False
    # cols
    for c in range(SIZE):
        if {solution[r][c] for r in range(SIZE)} != valid_set:
            return False
    # boxes
    for br in range(0, SIZE, BOX_ROWS):
        for bc in range(0, SIZE, BOX_COLS):
            box = {solution[r][c] for r in range(br, br + BOX_ROWS) for c in range(bc, bc + BOX_COLS)}
            if box != valid_set:
                return False
    return True


TARGET = {"easy": (24, 28), "medium": (18, 23), "hard": (12, 17)}
PER_DIFFICULTY = 10  # 10 x 3 = 30 total

puzzles = []
random.seed(42)

for difficulty, (lo, hi) in TARGET.items():
    count = 0
    attempts = 0
    while count < PER_DIFFICULTY:
        attempts += 1
        if attempts > 5000:
            print(f"WARN: only generated {count} for {difficulty}")
            break
        solution = generate_solution()
        if not verify_puzzle(solution):
            continue
        num_givens = random.randint(lo, hi)
        givens = make_puzzle(solution, num_givens)
        actual_givens = sum(1 for r in givens for c in r if c != "")
        puzzles.append({
            "difficulty": difficulty,
            "size": SIZE,
            "boxRows": BOX_ROWS,
            "boxCols": BOX_COLS,
            "givens": givens,
            "solution": solution,
        })
        count += 1
    print(f"  {difficulty}: {count} puzzles generated")

print(f"Total: {len(puzzles)} puzzles")

# Write to all languages
for lang in LANGS:
    path = BASE / f"{lang}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(puzzles, f, ensure_ascii=False, indent=2)
    print(f"  Written: {path}")

print("Done.")
