<script>
    import {onMount} from 'svelte';

    let searchQuery = '';
    let start_date = '';
    let end_date = '';
    let selectedBoardList = [];
    let qa_response = '';

    $: result1 = null;
    $: result2 = null;
    $: result3 = null;
    $: q_list = [];
    $: wordCloudImages = {};
    $: wordCloudVisible = {};

    let board_list = [];

    let expanded = {};
    let boardListExpanded = false;
    let dateSelectionExpanded = false;
    let dateOption = '1년';

    onMount(() => {
        setDateRange('1년');
        const params = new URLSearchParams(window.location.search);
        let access_token = localStorage.getItem('access_token') || '';
        searchQuery = params.get('query') || '';
        start_date = params.get('start_date') || '';
        end_date = params.get('end_date') || '';
        selectedBoardList = params.get('board') ? params.get('board').split(',') : [];

        const apiUrl = 'https://searchapi.betatester772.dev/';

        if (!searchQuery) {
            window.location = '/';
        }

        if (access_token) {
            let query_params = "q=" + searchQuery;
            if (start_date) {
                query_params = query_params + "&start_date=" + start_date;
            }
            if (end_date) {
                query_params = query_params + "&end_date=" + end_date;
            }
            if (selectedBoardList.length > 1) {
                query_params = query_params + "&board=[" + selectedBoardList.join(',').substring(0, selectedBoardList.join(',').length) + "]";
            } else if (selectedBoardList.length === 1) {
                query_params = query_params + "&board=[" + selectedBoardList[0] + "]";
            }

            fetch(apiUrl + 'board', {
                method: 'get',
                headers: {
                    'accept': 'application/json',
                    'Authorization': 'Bearer ' + access_token,
                }
            })
                .then(response => response.json())
                .then(data => {
                    board_list = data.result;
                    if (selectedBoardList.length === 0)
                        selectedBoardList = board_list;
                })
                .catch(error => console.error('Error:', error));

            if (searchQuery.endsWith('?')) {
                fetch(apiUrl + 'qa?' + query_params, {
                    method: 'get',
                    headers: {
                        'accept': 'application/json',
                        'Authorization': 'Bearer ' + access_token
                    }
                })
                    .then(response => response.ok ? response.json() : Promise.reject(response))
                    .then(data => {
                        qa_response = data.result;
                    })
                    .catch(error => console.error('Error:', error));
            }

            function checkResponse(response) {
                if (response.status === 200) {
                    return response.json();
                } else if (response.status === 401) {
                    localStorage.removeItem('access_token');
                    access_token = '';
                    window.location.href = 'https://sso.betatester772.dev/login?redirect=' + window.location.origin;
                } else {
                    return Promise.reject(response);
                }
            }

            let fetchRequests = [
                fetch(apiUrl + 'search/1?' + query_params, {
                    method: 'get',
                    headers: {
                        'accept': 'application/json',
                        "Authorization": "Bearer " + access_token
                    },
                }).then(response => response.ok ? response.json() : Promise.reject(response)),

                fetch(apiUrl + 'search/2?' + query_params, {
                    method: 'get',
                    headers: {
                        'accept': 'application/json',
                        "Authorization": "Bearer " + access_token
                    },
                }).then(response => response.ok ? response.json() : Promise.reject(response)),

                fetch(apiUrl + 'search/3?' + query_params, {
                    method: 'get',
                    headers: {
                        'accept': 'application/json',
                        "Authorization": "Bearer " + access_token
                    },
                }).then(checkResponse),
            ];

            Promise.all(fetchRequests)
                .then(results => {
                    [result1, result2, result3] = results;

                    function removeDuplicates(result, otherResults) {
                        let resultTextSet = new Set(result.result.map(item => item.content_text));
                        otherResults.forEach(otherResult => {
                            otherResult.result = otherResult.result.filter(item => !resultTextSet.has(item.content_text));
                        });
                    }

                    if (result1) {
                        q_list = result1.q;
                        removeDuplicates(result1, [result2, result3]);
                    }
                    if (result2) {
                        q_list = result2.q;
                        removeDuplicates(result2, [result1, result3]);
                    }
                    if (result3) {
                        q_list = result3.q;
                        removeDuplicates(result3, [result1, result2]);
                    }
                })
                .catch(error => console.error('Error:', error));
        } else {
            window.location.href = 'https://sso.betatester772.dev/login?redirect=' + window.location.origin;
        }
    });

    function redirectToSearch() {
        if (!searchQuery) return;
        let queryParams = `query=${encodeURIComponent(searchQuery)}`;
        if (start_date) queryParams += `&start_date=${start_date}`;
        if (end_date) queryParams += `&end_date=${end_date}`;
        if (selectedBoardList.length > 1) queryParams += `&board=${selectedBoardList.join(',')}`;
        else if (selectedBoardList.length === 1) queryParams += `&board=${selectedBoardList[0]}`;
        window.location.href = `/search?${queryParams}`;
    }

    function redirectToLogin() {
        if (!localStorage.getItem('access_token')) {
            window.location.href = 'https://sso.betatester772.dev/login?redirect=' + window.location.origin;
        } else {
            return;
        }
    }

    function toggleExpand(index) {
        expanded[index] = !expanded[index];
    }

    function getSnippet(content, length = 100) {
        return content.length > length ? content.slice(0, length) + '...' : content;
    }

    function highlight(text, queryList) {
        queryList.forEach(query => {
            const regex = new RegExp(`(${query})`, 'gi');
            text = text.replace(regex, '<mark>$1</mark>');
        });
        return text;
    }

    function highlightAnswer(context, answer, start, end) {
        const snippetLength = 30;
        const beforeStart = Math.max(0, start - snippetLength);
        const afterEnd = Math.min(context.length, end + snippetLength);

        const beforeAnswer = context.slice(beforeStart, start);
        const afterAnswer = context.slice(end, afterEnd);

        const beforeEllipsis = beforeStart > 0 ? "..." : "";
        const afterEllipsis = afterEnd < context.length ? "..." : "";

        const highlightedAnswer = `<mark>${answer}</mark>`;

        return `${beforeEllipsis}${beforeAnswer}${highlightedAnswer}${afterAnswer}${afterEllipsis}`;
    }

    async function getWordCloud(item) {
        if (wordCloudVisible[item.idx]) {
            wordCloudVisible[item.idx] = false;
        } else if (wordCloudImages[item.idx]) {
            wordCloudVisible[item.idx] = true;
        } else {
            try {
                const response = await fetch(`http://localhost:8000/wordcloud/?idx=${item.idx}`, {
                    method: 'get',
                    headers: {
                        'accept': 'application/json',
                        'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                    }
                });
                if (response.ok) {
                    const blob = await response.blob();
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        wordCloudImages[item.idx] = reader.result;
                        wordCloudVisible[item.idx] = true;
                    };
                    reader.readAsDataURL(blob);
                } else {
                    console.error('Failed to fetch word cloud:', response.status);
                }
            } catch (error) {
                console.error('Error fetching word cloud:', error);
            }
        }
    }

    function setDateRange(option) {
        const now = new Date();
        let start, end;

        switch (option) {
            case '1일':
                start = end = now;
                break;
            case '1주':
                start = new Date(now.setDate(now.getDate() - 7));
                end = new Date();
                break;
            case '1달':
                start = new Date(now.setMonth(now.getMonth() - 1));
                end = new Date();
                break;
            case '6개월':
                start = new Date(now.setMonth(now.getMonth() - 6));
                end = new Date();
                break;
            case '1년':
                start = new Date(now.setFullYear(now.getFullYear() - 1));
                end = new Date();
                break;
            case '직접설정':
                start_date = '';
                end_date = '';
                return;
        }

        start_date = start.toISOString().split('T')[0];
        end_date = end.toISOString().split('T')[0];
    }
</script>

<div class="w-full max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
    <div class="flex items-center mb-6">
        <a class="mr-4" href="/">
            <img src="/logo.png" alt="Home" width="32" height="32" class="w-8 h-8"
                 style="aspect-ratio:32/32;object-fit:cover"/>
        </a>
        <div class="flex-1 relative">
            <input bind:value={searchQuery} on:keydown={(e) => e.key === 'Enter' && redirectToSearch()}
                   on:click={redirectToLogin}
                   class="flex border bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 w-full h-10 pl-10 pr-32 rounded-md border-gray-300 focus:border-primary focus:ring-primary"
                   type="search" placeholder="검색어 입력"/>
            <button on:click={redirectToSearch}
                    class="inline-flex items-center justify-center whitespace-nowrap bg-emerald-500 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-primary/90 py-2 absolute top-0 right-0 h-10 px-4 rounded-md bg-primary text-primary-foreground"
                    type="submit">
                Search
            </button>
        </div>
    </div>
    <div class="mb-6">
        <div class="flex flex-wrap items-center">
            <div class="flex items-center mb-4 mr-4">
                <label for="date_range" class="mr-2 text-sm font-medium text-gray-700">Date Range:</label>
                <div class="relative">
                    <button on:click={() => dateSelectionExpanded = !dateSelectionExpanded}
                            class="border border-gray-300 px-6 py-2 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary">
                        {dateOption}
                    </button>
                    {#if dateSelectionExpanded}
                        <div class="absolute mt-1 w-full bg-white shadow-lg rounded-md z-10">
                            <ul class="date-range-list">
                                <li on:click={() => { setDateRange('1일'); dateOption = '1일'; dateSelectionExpanded = false; }}>
                                    1일
                                </li>
                                <li on:click={() => { setDateRange('1주'); dateOption = '1주'; dateSelectionExpanded = false; }}>
                                    1주
                                </li>
                                <li on:click={() => { setDateRange('1달'); dateOption = '1달'; dateSelectionExpanded = false; }}>
                                    1달
                                </li>
                                <li on:click={() => { setDateRange('6개월'); dateOption = '6개월'; dateSelectionExpanded = false; }}>
                                    6개월
                                </li>
                                <li on:click={() => { setDateRange('1년'); dateOption = '1년'; dateSelectionExpanded = false; }}>
                                    1년
                                </li>
                                <li on:click={() => { setDateRange('직접설정'); dateOption = '직접설정'; dateSelectionExpanded = false; }}>
                                    직접설정
                                </li>
                            </ul>
                        </div>
                    {/if}
                </div>
            </div>
            {#if dateOption === '직접설정'}
                <div class="flex items-center mb-4 mr-4">
                    <label for="start_date" class="mr-2 text-sm font-medium text-gray-700">Start Date:</label>
                    <input type="date" id="start_date" bind:value={start_date}
                           class="border border-gray-300 px-3 py-2 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"/>
                </div>
                <div class="flex items-center mb-4 mr-4">
                    <label for="end_date" class="mr-2 text-sm font-medium text-gray-700">End Date:</label>
                    <input type="date" id="end_date" bind:value={end_date}
                           class="border border-gray-300 px-3 py-2 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"/>
                </div>
            {/if}
            <div class="flex items-center mb-4">
                <label for="board_list" class="mr-2 text-sm font-medium text-gray-700">Board:</label>
                <div class="relative">
                    <button on:click={() => boardListExpanded = !boardListExpanded}
                            class="border border-gray-300 px-4 py-2 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary">
                        Select Boards
                    </button>
                    {#if boardListExpanded}
                        <div class="absolute mt-1 w-full bg-white shadow-lg rounded-md z-10 max-h-64 overflow-y-auto">
                            <ul>
                                {#each board_list as board}
                                    <li>
                                        <label>
                                            <input type="checkbox" value={board} bind:group={selectedBoardList}/>
                                            {board}
                                        </label>
                                    </li>
                                {/each}
                            </ul>
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>
    <div class="grid gap-6">
        {#if !result1 && !result2 && !result3}
            <div class="flex items-center justify-center h-64">
                <p class="text-gray-500">검색중 이거나 검색 결과가 없습니다.</p>
            </div>
        {/if}
        {#if result1}
            {#if qa_response.length > 0}
                <div class="qa-result border border-gray-300 rounded-md p-4">
                    <h2 class="text-xl font-bold mb-4">Q&A Result</h2>
                    {#each qa_response as qa}
                        <div class="qa-item mb-6">
                            <h3 class="text-lg font-semibold">Q: {qa.question}</h3>
                            <p class="text-gray-800">
                                {@html highlightAnswer(qa.context.content_text, qa.answer, qa.start, qa.end)}</p>
                        </div>
                    {/each}
                </div>
            {/if}
            {#each result1.result as item, index}
                <div class="flex items-start">
                    <div>
                        <h3 class="text-lg font-bold mb-1">
                            <a class="hover:text-primary" target="_blank" href={item.link}>
                                {item.title}
                            </a>
                            <a on:click={() => getWordCloud(item)}
                               class="text-gray-500 mb-2 text-xs hover:text-emerald-700 cursor-pointer">[워드 클라우드]</a>
                        </h3>
                        <p class="text-gray-500 mb-2">
                            {item.writer} : {item.date.substring(0, 10)}
                        </p>
                        <p class="text-gray-500 mb-2">
                            {@html highlight(expanded[index] ? item.content_text.replace(/\n/g, '<br>') : getSnippet(item.content_text.replace(/\n/g, '<br>')), q_list)}
                            <span class="more-button text-emerald-700 hover:text-emerald-700 cursor-pointer"
                                  on:click={() => toggleExpand(index)}>
                                {@html expanded[index] ? '<br/>접기' : '더보기'}
                            </span>
                            {#if wordCloudVisible[item.idx]}
                                <img src={wordCloudImages[item.idx]} alt="Word Cloud" class="mt-2"/>
                            {/if}
                        </p>
                    </div>
                </div>
                <hr class="border-gray-300"/>
            {/each}
        {/if}
        {#if result2}
            {#each result2.result as item, index}
                <div class="flex items-start">
                    <div>
                        <h3 class="text-lg font-bold mb-1">
                            <a class="hover:text-primary" target="_blank" href={item.link}>
                                {item.title}
                            </a>
                            <a on:click={() => getWordCloud(item)}
                               class="text-gray-500 mb-2 text-xs hover:text-emerald-700 cursor-pointer">[워드 클라우드]</a>
                        </h3>
                        <p class="text-gray-500 mb-2">
                            {item.writer} : {item.date.substring(0, 10)}
                        </p>
                        <p class="text-gray-500 mb-2">
                            {@html highlight(expanded[index] ? item.content_text.replace(/\n/g, '<br>') : getSnippet(item.content_text.replace(/\n/g, '<br>')), q_list)}
                            <span class="more-button text-emerald-700 hover:text-emerald-700 cursor-pointer"
                                  on:click={() => toggleExpand(index)}>
                                {@html expanded[index] ? '<br/>접기' : '더보기'}
                            </span>
                            {#if wordCloudVisible[item.idx]}
                                <img src={wordCloudImages[item.idx]} alt="Word Cloud" class="mt-2"/>
                            {/if}
                        </p>
                    </div>
                </div>
                <hr class="border-gray-300"/>
            {/each}
        {/if}
        {#if result3}
            {#each result3.result as item, index}
                <div class="flex items-start">
                    <div>
                        <h3 class="text-lg font-bold mb-1">
                            <a class="hover:text-primary" target="_blank" href={item.link}>
                                {item.title}
                            </a>
                            <a on:click={() => getWordCloud(item)}
                               class="text-gray-500 mb-2 text-xs hover:text-emerald-700 cursor-pointer">[워드 클라우드]</a>
                        </h3>
                        <p class="text-gray-500 mb-2">
                            {item.writer} : {item.date.substring(0, 10)}
                        </p>
                        <p class="text-gray-500 mb-2">
                            {@html highlight(expanded[index] ? item.content_text.replace(/\n/g, '<br>') : getSnippet(item.content_text.replace(/\n/g, '<br>')), q_list)}
                            <span class="more-button text-emerald-700 hover:text-emerald-700 cursor-pointer"
                                  on:click={() => toggleExpand(index)}>
                                {@html expanded[index] ? '<br/>접기' : '더보기'}
                            </span>
                            {#if wordCloudVisible[item.idx]}
                                <img src={wordCloudImages[item.idx]} alt="Word Cloud" class="mt-2"/>
                            {/if}
                        </p>
                    </div>
                </div>
                <hr class="border-gray-300"/>
            {/each}
        {/if}
    </div>
</div>
