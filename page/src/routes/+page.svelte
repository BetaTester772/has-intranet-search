<script>
    import {onMount} from 'svelte';

    let token = '';
    let origin = '';
    let searchQuery = '';
    $: _access_token = false;


    onMount(() => {
            const params = new URLSearchParams(window.location.search);
            // access_token from localStorage
            let access_token = localStorage.getItem('access_token') || '';
            token = params.get('token')
            origin = window.location.origin
            if (token) {
                fetch('https://ssoapi.betatester772.dev/api/v1/auth/token', {
                    method: 'POST',
                    headers: {
                        'accept': 'application/json',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: new URLSearchParams({
                        grant_type: '',
                        username: origin,
                        password: token,
                        scope: '',
                        client_id: '',
                        client_secret: ''
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.access_token) {
                            access_token = data.access_token;
                        }
                        localStorage.setItem('access_token', access_token);
                        window.location = '/';
                    })
                    .catch(error => console.error('Error:', error));
            }

            if (access_token) {
                fetch('https://ssoapi.betatester772.dev/api/v1/auth/check?site=' + origin, {
                    method: 'POST',
                    headers: {
                        'accept': 'application/json',
                        'Content-Type': 'application/json',
                        "Authorization": "Bearer " + access_token
                    },
                })
                    .then(response => {
                        if (response.status === 204) {
                            _access_token = true;
                        } else if (response.status === 401) {
                            localStorage.removeItem('access_token');
                            access_token = '';
                        }
                    })
                    .catch(error => console.error('Error:', error));
            }
        }
    )
    ;

    function redirectToSearch() {
        redirectToLogin();
        if (!searchQuery) return;
        window.location.href = `/search?query=${encodeURIComponent(searchQuery)}`;
    }

    function redirectToLogin() {
        if (!localStorage.getItem('access_token')) {
            window.location.href = 'https://sso.betatester772.dev/login?redirect=' + window.location.origin;
        } else {
            return;
        }
    }

</script>

<!--
// v0 by Vercel.
// https://v0.dev/t/BGDiX7cKXvd
-->

{#if token}
    <div class="fixed top-0 left-0 z-50 w-full h-full bg-black bg-opacity-50 flex items-center justify-center">
        <div class="bg-white p-8 rounded-lg shadow-lg">
            <h2 class="text-xl font-semibold mb-4">로그인 중...</h2>
            <p>로그인 중입니다. 잠시만 기다려주세요.</p>
        </div>
    </div>
{:else}
    <div class="flex flex-col items-center justify-center h-screen bg-gray-100">
        <div class="flex flex-col items-center mb-8 gap-y-2">
            <img
                    src="/logo.png"
                    alt="Hana Intranet Search Logo"
                    width="272"
                    height="272"
                    class="mb-4"
                    style="aspect-ratio: 272 / 272; object-fit: cover;"
            />
            <h1 class="text-4xl font-bold text-cyan-800">Hana Intranet Search</h1>
            <div class="w-full max-w-[584px] relative">
                <input bind:value={searchQuery} on:keydown={(e) => e.key === 'Enter' && redirectToSearch()}
                       class="flex h-10 border border-input bg-background text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 w-full px-5 py-3 rounded-full shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                       placeholder="검색어 입력" type="text"/>
                <button class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 absolute top-1/2 right-3 transform -translate-y-1/2"
                        on:click={redirectToSearch}>
                    <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="24"
                            height="24"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            class="w-5 h-5"
                    >
                        <circle cx="11" cy="11" r="8"></circle>
                        <path d="m21 21-4.3-4.3"></path>
                    </svg>
                </button>
            </div>
        </div>
        {#if !_access_token}
            <div class="flex justify-end w-full max-w-[1100px] px-4">
                <a href="https://sso.betatester772.dev/login?redirect=http://localhost:5173">
                    <button class="inline-flex items-center bg-emerald-500 justify-center whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 rounded-full absolute top-0 right-0">
                        로그인
                    </button>
                </a>
            </div>
        {/if}
    </div>
{/if}