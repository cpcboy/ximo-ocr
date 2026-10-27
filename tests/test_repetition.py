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


def test_v2_preserves_unique_numbered_records_and_amounts() -> None:
    text = '\n\n'.join(f'Entry {i:03d}: shipment ID MX-{2000+i}; units {i+3}.' for i in range(1, 121))
    result = trim_repetitive_tail(text, preserve_numbers=True)
    assert result.text == text and not result.finding.detected
    # Existing/v1 behavior stays explicitly unchanged; never rewrite old jobs.
    assert trim_repetitive_tail(text).finding.detected


def test_v2_still_detects_a_real_identical_loop() -> None:
    sentence = 'The same item number 104 costs 99.25 and repeats without any new information. '
    result = trim_repetitive_tail('Introduction to the invoice.\n' + sentence * 30, preserve_numbers=True)
    assert result.finding.detected and result.finding.removed_chars > 100


def test_v2_keeps_long_common_templates_with_distinct_numbers() -> None:
    text = '\n'.join(f'Entry {i:03d}: This shipment contains the following items and must be delivered '
                     f'to the designated address before the scheduled collection time. Quantity {i+3}.'
                     for i in range(1, 121))
    result = trim_repetitive_tail(text, preserve_numbers=True)
    assert result.text == text and not result.finding.detected


def test_v2_keeps_decimal_punctuation_and_chinese_differences() -> None:
    text = '\n'.join(f'商品{chr(0x4e00+i)}: Amount {i}.25; serial ID A-{i}-34. Common repeated description.'
                     for i in range(120))
    assert trim_repetitive_tail(text, preserve_numbers=True).text == text
