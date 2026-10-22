from backend.repetition import (
    analyze_repetitive_tail,
    find_exact_token_loop,
    trim_repetitive_tail,
)


def test_keeps_normal_text_and_two_legitimate_repetitions() -> None:
    paragraph = "This is a legitimate repeated instruction for the learner. "
    topics = [
        "airport",
        "bakery",
        "castle",
        "doctor",
        "engine",
        "forest",
        "garden",
        "harbor",
        "island",
        "jacket",
        "kitchen",
        "library",
        "market",
        "notebook",
        "office",
        "painter",
        "question",
        "river",
        "station",
        "theater",
    ]
    middle = " ".join(
        f"Different material about the {topic} appears between the two examples."
        for topic in topics
    )
    text = (
        "Introduction " * 80
        + paragraph
        + middle
        + paragraph
    )
    result = trim_repetitive_tail(text)
    assert result.text == text
    assert not result.finding.detected


def test_trims_a_repeated_sentence_tail() -> None:
    prefix = "A normal page contains useful material. " * 45
    loop = (
        "Everyone enjoyed the movie even though the ending was sad and "
        "the class discussed the final scene together. "
    )
    result = trim_repetitive_tail(prefix + loop * 14)
    assert result.finding.detected
    assert result.finding.removed_chars > len(loop) * 8
    assert result.text.count("Everyone enjoyed the movie") <= 2


def test_normalizes_changing_numbers_inside_a_loop() -> None:
    prefix = "Grammar explanation and examples appear before the exercise. " * 35
    loop = "".join(
        f"{number} We have lived in this town since 2010 and rented this house "
        "for the last two months. "
        for number in range(100, 145)
    )
    result = trim_repetitive_tail(prefix + loop)
    assert result.finding.detected
    assert "144 We have lived" not in result.text


def test_closes_html_table_after_trimming() -> None:
    prefix = "<table><tr><td>Header</td><td>Meaning</td></tr>"
    row = (
        "<tr><td>arrange</td><td>I arranged to support the scientist theory "
        "during the discussion today.</td></tr>"
    )
    result = trim_repetitive_tail(prefix + row * 18 + "</table>")
    assert result.finding.detected
    assert result.text.endswith("</table>")
    assert result.text.count("<table>") == result.text.count("</table>")


def test_detects_short_exact_token_cycles() -> None:
    history = list(range(150)) + [7, 8, 9, 10] * 30
    match = find_exact_token_loop(history)
    assert match is not None
    assert match["period"] == 4
    assert match["repeats"] >= 24


def test_does_not_flag_nonrepeating_tokens() -> None:
    assert find_exact_token_loop(list(range(500))) is None


def test_analysis_reports_metrics_without_trimming_clean_content() -> None:
    clean = " ".join(f"word{index}" for index in range(500))
    finding = analyze_repetitive_tail(clean)
    assert not finding.detected
