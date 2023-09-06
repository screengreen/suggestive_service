import io

import pytest
import app
from app import (
    Node,
    ReversedTrie,
    Suggester,
    Trie,
    app,
    count_queries,
    preprocess_query,
)
from fastapi.testclient import TestClient


# Enhanced Fixtures
@pytest.fixture
def sample_node():
    node = Node()
    return node


@pytest.fixture
def sample_trie():
    trie = Trie()
    trie.add_query("apple", 1.0)
    trie.add_query("app", 2.0)
    trie.add_query("application", 3.0)
    trie.add_query("triple apple", 4.0)
    trie.add_query("banana split", 5.0)
    trie.add_query("banana", 6.0)
    trie.add_query("grape juice", 7.0)
    return trie


@pytest.fixture
def sample_reverse_trie():
    rtrie = ReversedTrie()
    rtrie.add_query("apple pie", 1.0)
    rtrie.add_query("apple", 2.0)
    rtrie.add_query("orange juice", 3.0)
    rtrie.add_query("grape", 4.0)
    rtrie.add_query("mango shake", 5.0)
    return rtrie


@pytest.fixture
def sample_suggester():
    suggester = Suggester()
    suggester.fit(
        {
            "apple pie": 1.0,
            "pie apple": 20.0,
            "triple threat": 2.0,
            "banana boat": 3.0,
            "grape juice": 4.0,
            "apple bubble": 1.0,
            "blueberry muffin": 5.0,
            "i love apple": 2.0,
        }
    )
    return suggester


# Tests


def test_preprocess_query():
    assert preprocess_query(" Hello,   ; World!") == "hello world"
    assert preprocess_query(",,,Example!    TEST...   ") == "example test"


def test_count_queries():
    file = io.StringIO(
        "\n".join(
            [
                "appLe 123",
                "apple  123;",
                "bana;na",
                "banana",
                "bananA",
            ]
        )
    )
    assert count_queries(file) == {"apple 123": 2.0, "banana": 3.0}


def test_node_initialization(sample_node):
    attrs = set(sample_node.__dict__.keys())
    assert attrs == {"is_end", "value", "children"}

    assert sample_node.is_end is False
    assert sample_node.value == 0
    assert not sample_node.children


def test_trie_initialization(sample_trie):
    attrs = set(sample_trie.__dict__.keys())
    assert attrs == {"root"}


# Enhanced Trie Test


def test_trie_functionality(sample_trie):
    # Count queries
    assert sample_trie.count_queries() == 7

    # Add and retrieve
    sample_trie.add_query("chocolate cake", 8.0)
    assert (8.0, "chocolate cake") in sample_trie.suffixes("choco")

    # Suffixes
    results = sample_trie.suffixes("ban")
    assert len(results) == 2
    assert (5.0, "banana split") in results
    assert (6.0, "banana") in results

    # Remove and test absence
    sample_trie.remove_query("apple")

    # Assert that "apple" is no longer in the trie
    assert (1.0, "apple") not in sample_trie.suffixes("appl")

    # Make sure other entries are still intact
    results = sample_trie.suffixes("ban")
    assert (5.0, "banana split") in results
    assert (6.0, "banana") in results

    # Make sure unrelated entries are unaffected
    assert (7.0, "grape juice") not in results

    # Attempt to remove an entry not present in the trie, should raise an exception
    try:
        sample_trie.remove_query("nonexistent")
        assert False, "Expected an exception when trying to remove a non-existent entry"
    except Exception as e:
        assert str(e) == "Query nonexistent not found!"

    # Suffixes
    results = sample_trie.suffixes("ban")
    assert (5.0, "banana split") in results
    assert (6.0, "banana") in results
    assert (7.0, "grape juice") not in results

    # Confirm that there are entries before clearing
    assert (
        sample_trie.count_queries() > 0
    )  # Assumes that `count_queries` method gives the number of entries

    # Use the clear method
    sample_trie.clear()

    # Ensure all entries are cleared
    assert sample_trie.count_queries() == 0

    # Ensure any previous suffixes are not available anymore
    assert not sample_trie.suffixes("ban")
    assert not sample_trie.suffixes("appl")
    assert not sample_trie.suffixes("grape")

    # Re-add a query and check
    sample_trie.add_query("apple", 1.0)
    assert (1.0, "apple") in sample_trie.suffixes("appl")
    assert sample_trie.count_queries() == 1


# Enhanced ReversedTrie Test


def test_reverse_trie_functionality(sample_reverse_trie):
    # Count queries
    assert sample_reverse_trie.count_queries() >= 5

    # Prefixes
    results = sample_reverse_trie.prefixes("pie")
    assert len(results) == 1
    assert (1.0, "apple pie") in results

    # Prefixes
    results = sample_reverse_trie.prefixes("shake")
    assert (5.0, "mango shake") in results
    assert (4.0, "grape") not in results


# Enhanced Suggester Test


def test_suggester_functionality(sample_suggester):
    # Count queries
    assert sample_suggester.count_queries() >= 8

    # Suggest Query
    results = sample_suggester.suggest_query("ple")
    assert len(results) == len(set(results))
    assert {
        (20.0, "pie apple"),
        (1.0, "apple bubble"),
        (2.0, "i love apple"),
        (2.0, "triple threat"),
        (1.0, "apple pie"),
    } == set(results)

    # Suggest Removed Char
    results = sample_suggester.suggest_removed_char("applle")
    assert len(results) == 0

    # Suggest Last Words
    results = sample_suggester.suggest_last_words("i love apple")
    assert len(results) == len(set(results))
    assert (2.0, "i love apple") in results
    assert (20.0, "pie apple") in results


# FastAPI Test


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "query, k, expected_query",
    [
        ("", 10, ""),
        ("HeL", 3, "hel"),
        ("   ;;;   ", 5, ""),
        ("apple, ", 10, "apple"),
        ("asuS ;;;;", 100, "asus"),
    ],
)
def test_suggestions(query, k, expected_query, client):
    response = client.get(f"/suggest/?query={query}&k={k}")
    assert response.status_code == 200
    assert response.json()["query"] == expected_query
    assert isinstance(response.json()["suggestions"], list)
    assert len(response.json()["suggestions"]) <= k


def test_suggestions_recall(client):
    query = "lap"
    response = client.get(f"/suggest/?query={query}&k=20")
    assert response.status_code == 200

    correct = {
        "ring alarm 5piece kit",
        "samsung galaxy book flex",
        "microsoft surface laptop go",
        "samsung galaxy z fold 4",
        "samsung galaxy a42 5g",
        "microsoft surface laptop 4",
        "lg ultrafine 4k display",
        "sony playstation 5",
        "samsung galaxy buds 3",
        "bang olufsen beoplay h9",
        "samsung galaxy watch 4 classic",
        "samsung galaxy note 23",
        "samsung galaxy note 20 ultra",
        "razer blackwidow keyboard",
        "samsung galaxy tab s8 ultra",
        "samsung galaxy s22 ultra",
        "lg ultrafine 5k display 2023",
        "lg gram 17 laptop",
        "samsung galaxy buds pro",
        "samsung galaxy buds 2",
    }
    suggestions = set(response.json()["suggestions"])

    # calculate recall using set operations
    recall = len(correct.intersection(suggestions)) / len(correct)

    print(f"Correct: {correct}")
    print(f"Suggestions: {suggestions}")
    print(f"Recall {recall}")

    assert recall >= 0.5
