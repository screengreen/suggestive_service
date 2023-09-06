function clearSearch() {
    document.getElementById('query').value = '';
    clearSuggestions();
}

function clearSuggestions() {
    document.getElementById('suggestions').innerHTML = '';
    document.getElementById('search-box').classList.remove('show-suggestions');
}

async function getSuggestions() {
    var query = document.getElementById('query').value.toLowerCase();
    const response = await fetch(`/suggest/?query=${query}`);
    const data = await response.json();
    if (data.suggestions && data.suggestions.length > 0) {
        const formattedSuggestions = data.suggestions.map(suggestion => {
            const queryWords = data.query.split(' ');
            const suggestionWords = suggestion.split(' ');

            const resultWords = suggestionWords.map(word => {
                if (queryWords.includes(word)) {
                    return word; // Return word as it is if it's found in the query
                } else {
                    return '<text class="suffix">' + word + '</text>'; // Otherwise, underline it
                }
            });

            return '<div class="suggestion-item">' + resultWords.join(' ') + '</div>';
        });


        document.getElementById('search-box').classList.add('show-suggestions');
        document.getElementById('suggestions').innerHTML = formattedSuggestions.join('');

        // Add click event listeners to each suggestion
        document.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', function () {
                document.getElementById('query').value = this.textContent;
                getSuggestions();
            });
        });
    } else {
        clearSuggestions();
    }
}