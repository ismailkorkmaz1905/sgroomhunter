from __future__ import annotations


def count_letter_changes(left: str, right: str) -> int:
    if len(left) != len(right):
        return -1
    return sum(1 for left_char, right_char in zip(left, right) if left_char != right_char)


def validate_word_pool(language: str, words: list[str]) -> None:
    if not words:
        raise ValueError(f"{language} word pool is empty")
    normalized = [word.strip().lower() for word in words]
    if any(not word for word in normalized):
        raise ValueError(f"{language} word pool contains an empty word")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{language} word pool contains duplicates")


def validate_typo_pool(language: str, entries: list[dict]) -> None:
    if not entries:
        raise ValueError(f"{language} typo pool is empty")
    seen_correct = set()
    for index, entry in enumerate(entries, start=1):
        correct = str(entry.get("correct", "")).strip().lower()
        typo = str(entry.get("typo", "")).strip().lower()
        if not correct or not typo:
            raise ValueError(f"{language} typo #{index} has an empty value")
        if correct == typo:
            raise ValueError(f"{language} typo #{index} repeats the correct spelling")
        if correct in seen_correct:
            raise ValueError(f"{language} typo #{index} repeats a correct word: {correct}")
        seen_correct.add(correct)


def validate_ladder_pool(language: str, ladders: list[dict]) -> None:
    for index, puzzle in enumerate(ladders, start=1):
        path = puzzle["path"]
        if not path:
            raise ValueError(f"{language} ladder #{index} has an empty path")
        if path[0] != puzzle["start"]:
            raise ValueError(f"{language} ladder #{index} start mismatch: {path[0]} != {puzzle['start']}")
        if path[-1] != puzzle["target"]:
            raise ValueError(f"{language} ladder #{index} target mismatch: {path[-1]} != {puzzle['target']}")
        if len(path) != len(set(path)):
            raise ValueError(f"{language} ladder #{index} repeats a rung: {' -> '.join(path)}")
        if len({len(word) for word in path}) != 1:
            raise ValueError(f"{language} ladder #{index} mixes word lengths")
        for current_word, next_word in zip(path, path[1:]):
            difference = count_letter_changes(current_word, next_word)
            if difference != 1:
                raise ValueError(
                    f"{language} ladder #{index} invalid transition: {current_word} -> {next_word} ({difference})"
                )


def validate_chain_pool(language: str, words: list[str]) -> None:
    validate_word_pool(language, words)
    if len(words) < 10:
        raise ValueError(f"{language} chain pool is too small")


def validate_category_pool(language: str, rounds: list[dict]) -> None:
    if not rounds:
        raise ValueError(f"{language} category pool is empty")
    for index, round_data in enumerate(rounds, start=1):
        category = str(round_data.get("category", "")).strip()
        answer = str(round_data.get("answer", "")).strip()
        options = [str(item).strip() for item in round_data.get("options", [])]
        if not category or not answer:
            raise ValueError(f"{language} category round #{index} is missing text")
        if len(options) < 4:
            raise ValueError(f"{language} category round #{index} has fewer than 4 options")
        if answer not in options:
            raise ValueError(f"{language} category round #{index} answer is missing from options")
        if len(options) != len(set(options)):
            raise ValueError(f"{language} category round #{index} has duplicate options")


def validate_crossword_pool(language: str, puzzles: list[dict]) -> None:
    if not puzzles:
        raise ValueError(f"{language} crossword pool is empty")

    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}
    for puzzle_index, puzzle in enumerate(puzzles, start=1):
        size = int(puzzle["size"])
        blocks = {tuple(block) for block in puzzle.get("blocks", [])}
        if size < 3:
            raise ValueError(f"{language} crossword #{puzzle_index} is too small")
        for row, col in blocks:
            if row < 0 or col < 0 or row >= size or col >= size:
                raise ValueError(f"{language} crossword #{puzzle_index} has an out-of-bounds block")

        occupied: dict[tuple[int, int], str] = {}
        for entry_index, entry in enumerate(puzzle.get("entries", []), start=1):
            direction = entry["direction"]
            answer = str(entry["answer"]).strip().lower()
            row = int(entry["row"])
            col = int(entry["col"])
            if direction not in {"across", "down"}:
                raise ValueError(f"{language} crossword #{puzzle_index} entry #{entry_index} has a bad direction")
            if not answer:
                raise ValueError(f"{language} crossword #{puzzle_index} entry #{entry_index} is empty")

            for offset, letter in enumerate(answer):
                current_row = row + (offset if direction == "down" else 0)
                current_col = col + (offset if direction == "across" else 0)
                if current_row >= size or current_col >= size:
                    raise ValueError(f"{language} crossword #{puzzle_index} entry #{entry_index} overflows the grid")
                if (current_row, current_col) in blocks:
                    raise ValueError(f"{language} crossword #{puzzle_index} entry #{entry_index} hits a block")
                existing = occupied.get((current_row, current_col))
                if existing and existing != letter:
                    raise ValueError(
                        f"{language} crossword #{puzzle_index} conflicting letters at {(current_row, current_col)}"
                    )
                occupied[(current_row, current_col)] = letter

        difficulty = str(puzzle.get("difficulty", "")).strip().lower()
        if difficulty:
            if difficulty not in difficulty_counts:
                raise ValueError(f"{language} crossword #{puzzle_index} has an invalid difficulty")
            difficulty_counts[difficulty] += 1
        elif size <= 3:
            difficulty_counts["easy"] += 1
        elif size == 4:
            difficulty_counts["medium"] += 1
        else:
            difficulty_counts["hard"] += 1

    for difficulty, count in difficulty_counts.items():
        if count < 3:
            raise ValueError(f"{language} crossword pool has fewer than 3 {difficulty} puzzles")


def validate_sudoku_pool(language: str, puzzles: list[dict]) -> None:
    if not puzzles:
        raise ValueError(f"{language} sudoku pool is empty")

    valid_digits = {"1", "2", "3", "4", "5", "6"}
    for puzzle_index, puzzle in enumerate(puzzles, start=1):
        size = int(puzzle.get("size", 0))
        box_rows = int(puzzle.get("boxRows", 0))
        box_cols = int(puzzle.get("boxCols", 0))
        givens = puzzle.get("givens", [])
        solution = puzzle.get("solution", [])
        difficulty = str(puzzle.get("difficulty", "")).strip().lower()

        if size != 6 or box_rows != 2 or box_cols != 3:
            raise ValueError(f"{language} sudoku #{puzzle_index} must be 6x6 with 2x3 boxes")
        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError(f"{language} sudoku #{puzzle_index} has an invalid difficulty")
        if len(givens) != size or len(solution) != size:
            raise ValueError(f"{language} sudoku #{puzzle_index} has the wrong row count")

        for row_index, (given_row, solution_row) in enumerate(zip(givens, solution), start=1):
            if len(given_row) != size or len(solution_row) != size:
                raise ValueError(f"{language} sudoku #{puzzle_index} row #{row_index} has the wrong length")
            given_values = [str(value) if value is not None else "" for value in given_row]
            solution_values = [str(value) for value in solution_row]

            if set(solution_values) != valid_digits:
                raise ValueError(f"{language} sudoku #{puzzle_index} row #{row_index} solution is invalid")
            for given_value, solution_value in zip(given_values, solution_values):
                if given_value not in {"", "0"} | valid_digits:
                    raise ValueError(f"{language} sudoku #{puzzle_index} has an invalid given")
                if given_value not in {"", "0"} and given_value != solution_value:
                    raise ValueError(f"{language} sudoku #{puzzle_index} givens do not match solution")

        for col in range(size):
            column_values = {str(solution[row][col]) for row in range(size)}
            if column_values != valid_digits:
                raise ValueError(f"{language} sudoku #{puzzle_index} column #{col + 1} is invalid")

        for start_row in range(0, size, box_rows):
            for start_col in range(0, size, box_cols):
                box_values = {
                    str(solution[row][col])
                    for row in range(start_row, start_row + box_rows)
                    for col in range(start_col, start_col + box_cols)
                }
                if box_values != valid_digits:
                    raise ValueError(f"{language} sudoku #{puzzle_index} has an invalid box")


def validate_all_datasets(
    words_by_language: dict[str, list[str]],
    typos_by_language: dict[str, list[dict]],
    ladders_by_language: dict[str, list[dict]],
    chains_by_language: dict[str, list[str]],
    categories_by_language: dict[str, list[dict]],
    crosswords_by_language: dict[str, list[dict]],
    sudokus_by_language: dict[str, list[dict]],
) -> None:
    for language, words in words_by_language.items():
        validate_word_pool(language, words)
    for language, entries in typos_by_language.items():
        validate_typo_pool(language, entries)
    for language, ladders in ladders_by_language.items():
        validate_ladder_pool(language, ladders)
    for language, chains in chains_by_language.items():
        validate_chain_pool(language, chains)
    for language, categories in categories_by_language.items():
        validate_category_pool(language, categories)
    for language, puzzles in crosswords_by_language.items():
        validate_crossword_pool(language, puzzles)
    for language, puzzles in sudokus_by_language.items():
        validate_sudoku_pool(language, puzzles)
