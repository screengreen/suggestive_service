import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import tqdm
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.utils import download_yandex_disk

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

QUERIES_URL = "https://disk.yandex.ru/d/yQt-jfBSzTs1eA"
QUERIES_PATH = "data/queries.txt"


@dataclass
class Node:
    """
    Represents a Trie node.

    Attributes
    ----------
    children : Dict[str, "Node"]
        Dictionary of child nodes.
    is_end : bool
        Indicates if this node is an ending character of a stored string.
    value : float
        Value associated with the stored string.
    """

    children: Dict[str, "Node"] = field(default_factory=dict)
    
    value: float = 0


@dataclass
class Trie:
    """
    A Trie data structure for efficient string manipulation and retrieval.

    Attributes
    ----------
    root : Node
        The root node of the Trie.
    """

    root: Node = field(default_factory=Node)

    def add_query(self, query: str, value: float) -> None:
        """
        Adds a single query string to the Trie.

        Parameters
        ----------
        query : str
            The string to be added to the Trie.
        value : float
            The value associated with the query.
        """
        node = self.root

        for char in query:
            if char not in node.children:
                node.children[char] = Node()
            node = node.children[char]

        node.value = value    

    def remove_query(self, query: str) -> None:
        """
        Removes a single query string from the Trie.

        Parameters
        ----------
        query : str
            The string to be removed from the Trie.

        Raises
        ------
        Exception:
            If the query is not found in the Trie.

        >>> raise Exception(f"Query {query} not found!")
        """
        node = self.root
        path = [node]  # Keep track of the path to the query
        for char in query:
            if char not in node.children:
                raise Exception(f"Query {query} not found!")
            path.append(node)
            node = node.children[char]

        # Remove the query by clearing its value and marking the last node as not an end
        node.value = 0
        node.is_end = False

        # Clean up empty nodes along the path
        for i in range(len(path) - 1, -1, -1):
            if not path[i].children and not path[i].is_end and path[i] != self.root:
                del path[i - 1].children[path[i - 1]]
            else:
                break



    def clear(self) -> None:
        """Clears all the entries in the Trie."""
        self.root.children.clear()

    def suffixes(
        self,
        prefix: str,
    ) -> List[Tuple[float, str]]:
        """
        Returns all suffixes of the given prefix.

        Notes
        -----
        Here by suffix we mean string prefix + suffix.

        Parameters
        ----------
        prefix : str
            The prefix string.

        Returns
        -------
        List[Tuple[float, str]]
            List of (value, suffix) pairs.

        Examples
        --------
        Given queries: "apple", "app", "application", "triple"

        >>> trie = Trie()
        >>> trie.add_query("apple", 1.0)
        >>> trie.add_query("app", 2.0)
        >>> trie.add_query("application", 3.0)
        >>> trie.add_query("triple", 4.0)
        >>> trie.suffixes("app")
        [(3.0, 'application'), (2.0, 'app'), (1.0, 'apple')]
        """
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]

        def _collect_suffixes(node, current_suffix):
            result = []
            if node.value > 0.0:
                result.append((node.value, current_suffix))
            for char, child_node in node.children.items():
                result.extend(_collect_suffixes(child_node, current_suffix + char))
            return result

        return sorted(_collect_suffixes(node, prefix), reverse=True)

    


    def count_queries(self) -> int:
        """
        Returns the number of queries stored in the Trie.

        Returns
        -------
        int
            The number of queries stored in the Trie.
        """
        def _count_recursive(node):
            count = 0
            if node.value > 0.0:
                count += 1
            for child_node in node.children.values():
                count += _count_recursive(child_node)
            return count
    
        return _count_recursive(self.root)


@dataclass
class ReversedTrie(Trie):
    """
    A Reversed Trie data structure derived from the Trie,
    which efficiently manipulates and retrieves reversed strings.

    Give a possibility to find prefixes of the given suffix.

    Notes
    -----
    The ReversedTrie is derived from the Trie class, which means that
    all the methods of the Trie class are available for the ReversedTrie class.

    Use super() to call the methods of the Trie class.
    """

    root: Node = field(default_factory=Node)

    def add_query(self, query: str, value: float) -> None:
        """
        Adds a single reversed query string to the Trie.

        Parameters
        ----------
        query : str
            The string whose reverse will be added to the Trie.
        value : float
            The value associated with the query.

        Examples
        --------
        Given queries: "apple", "triple"

        >>> rtrie = ReversedTrie()
        >>> rtrie.add_query("apple", 1.0)
        """
        node = self.root
        query = query[::-1]

        for char in query:
            if char not in node.children:
                node.children[char] = Node()
            node = node.children[char]

        node.value = value    

    def prefixes(self, suffix: str) -> List[Tuple[float, str]]:
        """
        Returns all prefixes of the given suffix.

        Notes
        -----
        Here by prefix we mean string prefix + suffix.

        Parameters
        ----------
        suffix : str
            The suffix string.

        Returns
        -------
        List[Tuple[float, str]]
            List of (value, prefix) pairs.

        Examples
        --------
        >>> rtrie = ReversedTrie()
        >>> rtrie.add_query("apple", 1.0)
        >>> ... # add more queries from apple
        >>> rtrie.add_query("triple", 2.0)
        >>> ... # add more queries from triple
        >>> rtrie.prefixes("pl")
        [(2.0, 'tripl'), (1.0, 'appl')] # "pl" is common
        """
        result = []

        end_of_suffix = suffix[-1] if suffix else ''
        starting_nodes = []
        def find_end_of_suffix(node):
            if node.value is not None:
                pass
            
            for child in node.children:
                
                if end_of_suffix in node.children:
                    starting_nodes.append(node.children[end_of_suffix])
                find_end_of_suffix(node.children[child])
                
        find_end_of_suffix(self.root)
 
        # Perform a depth-first search to collect prefixes
        def dfs(node, prefix):
            if node.value > 0.0:
                result.append((node.value, prefix[::-1]))  # Reversed prefix

            for char, child_node in node.children.items():
                dfs(child_node, prefix + char)

        for node in starting_nodes:
            dfs(node, suffix[-1])
        
        return result



@dataclass
class Suggester:
    """
    A class to provide string suggestions based on input
    using both standard and reverse Trie data structures.

    Notes
    -----
    Make sure that suggest_ methods return unique suggests Tuple.


    Attributes
    ----------
    trie : Trie
        A standard trie data structure for forward string manipulations.
    reversed_trie : ReversedTrie
        A reverse trie data structure for backward string manipulations.
    """

    trie: Trie = field(default_factory=Trie)
    reversed_trie: ReversedTrie = field(default_factory=ReversedTrie)

    def fit(self, queries: Dict[str, float]) -> None:
        """
        Fits the suggester with a dictionary of queries and associated values.

        Parameters
        ----------
        queries : Dict[str, float]
            A dictionary of query strings and their associated values.
        """
        for q, v in queries.items():
            # fit trie with preprocessed queries
            self.trie.add_query(q,v)

            # fit reversed trie with preprocessed queries
            # each query is used to fit the trie with all its ...
            self.reversed_trie.add_query(q,v)
            

    def count_queries(self) -> int:
        """
        Returns the total number of queries in both tries.

        Returns
        -------
        int
            Total number of queries.
        """
        return self.trie.count_queries() + self.reversed_trie.count_queries()

    def suggest_query(self, query: str) -> List[Tuple[float, str]]:
        """
        Provides suggestions based on a given query string.

        Also provides suggestions based on ReversedTrie prefixes.

        Hint
        ----
        Use the ReversedTrie prefixes method.

        Parameters
        ----------
        query : str
            The input string.

        Returns
        -------
        List[Tuple[float, str]]
            A list of suggested queries with their associated values.

        Examples
        --------
        >>> suggester = Suggester()
        >>> suggester.fit({"apple": 1.0, "triple": 2.0})
        >>> suggester.suggest_query("pl")
        [(1.0, 'apple'), (2.0, 'triple')]
        """
        # normal trie suffixes
        suffix_suggestions = self.trie.suffixes(query)

        # reversed trie prefixes
        prefix_suggestions = self.reversed_trie.prefixes(query[::-1])  # Reverse the query before using prefixes

        suggestions = list(set(suffix_suggestions + prefix_suggestions))

        return suffix_suggestions

    def suggest_removed_char(self, query: str) -> List[Tuple[float, str]]:
        """
        Provides suggestions based on the query after removing the last character.

        Return [] if the query length is less than 2.

        Hint
        ----
        Reuse self.suggest_query instead of justs self.trie.suffixes.

        Parameters
        ----------
        query : str
            The input string.

        Returns
        -------
        List[Tuple[float, str]]
            A list of suggested queries with their associated values.
        """

        if len(query) < 2:
            return []

        # Remove the last character from the query
        modified_query = query[:-1]

        # Reuse the existing suggest_query function to get suggestions
        suggestions = self.suggest_query(modified_query)

        return suggestions

    def suggest_each_word(self, query: str) -> List[Tuple[float, str]]:
        """
        Provides suggestions based on each word in the query.

        Parameters
        ----------
        query : str
            The input string, typically containing multiple words.

        Returns
        -------
        List[Tuple[float, str]]
            A list of suggested queries with their associated values.

        Examples
        --------
        Psuedo code:
        query = "apple iphone banana"
        suggestions =
            + suggest_query("apple")
            + suggest_query("iphone")
            + suggest_query("banana")
        """
        words = query.split()  # Split the query into individual words
        all_suggestions = []

        # Iterate through each word and get suggestions using suggest_query
        for word in words:
            word_suggestions = self.suggest_query(word)
            all_suggestions.extend(word_suggestions)  # Add suggestions for this word to the list

        return all_suggestions


suggester = Suggester()


def preprocess_query(query: str) -> str:
    """
    Preprocess the given query string.

    Based on the queries.txt file understand
    how to preprocess the query string.

    Parameters
    ----------
    query : str
        The raw input string that needs to be preprocessed.

    Returns
    -------
    str
        The preprocessed query string.

    Examples
    --------
    >>> preprocess_query("  HelLo,  ;  World!  ")
    'hello world'
    """
    
    reg = re.compile('[^a-zA-Z0-9 ]')
    query = reg.sub('', query)
    query = re.sub(r'\s+', ' ', query).strip() 
    query = query.lower()
    return query


def count_queries(file) -> Dict[str, float]:
    """
    Counts the number of times each query appears in the file.

    The value of each query is defined by number of times
    the preprocess query (preprocess_query(q)) appears in the file.

    Parameters
    ----------
    file : file

    Returns
    -------
    Dict[str, float]
        A dictionary of query strings and their associated values.

    Examples
    --------
    file:
        appLe 123
        apple  123;
        bana;na
        banana
        bananA
    >>> with open("queries.txt", "r") as file:
    >>>     count_queries(file)
    {'apple 123': 2.0, 'banana': 3.0}
    """
    queries: Dict[str, float] = defaultdict(lambda: 0)
    rows = file.readlines()
    for q in tqdm.tqdm(rows):
        q = preprocess_query(q)
        if queries[q]:
            queries[q]+=1.0
        else:
            queries[q] = 1.0
    return queries


@app.on_event("startup")
async def startup_event() -> None:
    """
    Handles the startup event of the FastAPI application.
    Downloads the queries file and fit the suggester with the queries.

    The value of each query is defined by number of times
    the preprocess query (preprocess_query(q)) appears in the file.
    """
    # download the queries file
    print("Downloading queries file...")
    download_yandex_disk(QUERIES_URL, QUERIES_PATH)

    # load the queries file
    with open(QUERIES_PATH, "r") as file:
        queries = count_queries(file)

    # fit the suggester with the queries
    suggester.fit(queries=queries)
    

    print(f"Suggester fitted with {suggester.count_queries()} queries!")


@app.get("/suggest/")
def suggest(query: str, k: int = 10):
    """
    Provide search query suggestions based on the input query.

    Suggestions are sorted by their associated values in descending order.

    Parameters
    ----------
    query : str
        The input search query for which suggestions are needed.
    k : int, optional
        The number of suggestions required, by default 10.

    Returns
    -------
    Dict[str, List[str]]
        A dictionary containing the preprocessed query and the list of suggestions.

    Examples
    --------
    >>> suggestions("", k=10)
    {"query": "", "suggestions": []}
    >>> suggestions("HeL", k=3)
    {"query": "hel", "suggestions": ["hello world", "help", "helmet"]}
    """
    

    query = preprocess_query(query)

    # suggestions = ["hello world", ...] -> suggestions = []
    suggestions = []

    # Full query + substring search suggestions
    full_query_suggestions = suggester.suggest_query(query)
    suggestions.extend(full_query_suggestions)

    # Remove the last character of the query and then suggest
    # removed_char_suggestions = suggester.suggest_removed_char(query)
    # suggestions.extend(removed_char_suggestions)

    # Only if there are less than unique k suggestions
    # if len(set(suggestions)) < k:
    #     # N-last words suggestions
    #     n_last_words_suggestions = suggester.suggest_each_word(query)
    #     suggestions.extend(n_last_words_suggestions)

    # Sorting by value and taking top k
    suggestions.sort(reverse=True)
    top_k_suggestions = suggestions[:k]
    formatted_suggestions = [suggestion[1] for suggestion in top_k_suggestions]

    return {"query": query, "suggestions": formatted_suggestions}


@app.get("/")
def root(request: Request):
    """
    Returns html page of the application.

    Parameters
    ----------
    request : Request
        The request object.
    """
    return templates.TemplateResponse("index.html", {"request": request})
