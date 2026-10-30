(() => {
    "use strict";
    const form = document.getElementById("llm-search-form");
    if (!form) return;

    const root = document.getElementById("ai-search");
    const chatLog = document.getElementById("chat-log");
    const turnTemplate = document.getElementById("turn-template");
    const cardTemplate = document.getElementById("product-card-template");
    const prompt = form.elements.prompt;
    const button = form.querySelector("button[type=submit]");
    const wordCount = document.getElementById("search-word-count");
    const currency = new Intl.NumberFormat("id-ID");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    const POLL_DEADLINE_MS = 180000; // sama dengan LLM_LEASE_SECONDS
    let isSubmitting = false;

    // ---------- Validasi & penghitung kata ----------
    function updateWordCount() {
        const count = prompt.value.match(/\S+/gu)?.length || 0;
        const characters = Array.from(prompt.value).length;
        const overLimit = count > 500 || characters > 5000;
        const message = characters > 5000 ? "Maksimal 5.000 karakter, termasuk spasi. Persingkat pencarian." :
            (count > 500 ? "Maksimal 500 kata. Kurangi kata sebelum mencari." : "");
        wordCount.textContent = `${count}/500 kata${overLimit ? " — " + message : ""}`;
        wordCount.classList.toggle("text-danger", overLimit);
        wordCount.classList.toggle("text-white/70", !overLimit);
        prompt.setCustomValidity(message);
        prompt.setAttribute("aria-invalid", String(overLimit));
        button.disabled = isSubmitting || overLimit || !prompt.value.trim();
    }

    function autoGrow() {
        prompt.style.height = "auto";
        prompt.style.height = `${prompt.scrollHeight}px`;
    }

    prompt.addEventListener("input", () => { updateWordCount(); autoGrow(); });
    window.addEventListener("pageshow", updateWordCount);
    updateWordCount();

    // Enter = kirim, Shift+Enter = baris baru (seperti kolom chat).
    prompt.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            if (!button.disabled) form.requestSubmit();
        }
    });

    document.querySelectorAll("[data-example]").forEach(example => {
        example.addEventListener("click", () => {
            prompt.value = example.textContent.trim();
            updateWordCount();
            autoGrow();
            form.requestSubmit();
        });
    });

    // ---------- Tampilan percakapan ----------
    function newTurn(text) {
        const turn = turnTemplate.content.firstElementChild.cloneNode(true);
        turn.querySelector("[data-user-message]").textContent = text;
        chatLog.append(turn);
        root.dataset.state = "chat";
        turn.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
        return turn;
    }

    function interpretation(filters, degraded) {
        const lines = [];
        if (filters.keyword) lines.push(`Kata kunci: ${filters.keyword}`);
        if (filters.categories?.length) lines.push(`Kategori: ${filters.categories.join(", ")}`);
        if (filters.location) lines.push(`Lokasi: ${filters.location}`);
        if (filters.min_price != null) lines.push(`Harga minimum: Rp${currency.format(filters.min_price)}`);
        if (filters.max_price != null) lines.push(`Harga maksimum: Rp${currency.format(filters.max_price)}`);
        if (filters.in_stock) lines.push("Hanya produk yang tersedia");
        if (filters.sort === "price_asc") lines.push("Urutkan dari harga termurah");
        if (filters.sort === "price_desc") lines.push("Urutkan dari harga tertinggi");
        if (degraded) lines.push("Rekomendasi AI belum tersedia, memakai hasil filter");
        if (!lines.length) lines.push("Membaca permintaan dan mencocokkannya dengan katalog");
        return lines;
    }

    function finishThinking(turn, lines, failed) {
        const toggle = turn.querySelector("[data-thinking-toggle]");
        const label = turn.querySelector("[data-thinking-label]");
        const chevron = turn.querySelector("[data-thinking-chevron]");
        const content = turn.querySelector("[data-thinking-content]");
        label.classList.remove("thinking-shimmer");
        label.textContent = failed ? "Tidak dapat memproses" : "Selesai berpikir";
        if (!lines.length) return;
        content.replaceChildren(...lines.map(line => {
            const item = document.createElement("li");
            item.textContent = line;
            return item;
        }));
        toggle.disabled = false;
        chevron.classList.remove("hidden");
        toggle.addEventListener("click", () => {
            const open = content.hidden;
            content.hidden = !open;
            toggle.setAttribute("aria-expanded", String(open));
            chevron.classList.toggle("rotate-90", open);
        });
    }

    // Teks jawaban muncul bertahap, kata demi kata.
    async function streamText(element, text) {
        if (reduceMotion || !text) {
            element.textContent = text || "";
            return;
        }
        const tokens = text.match(/\S+\s*|\s+/g) || [];
        element.textContent = "";
        for (let i = 0; i < tokens.length; i += 2) {
            element.textContent += tokens.slice(i, i + 2).join("");
            await sleep(28);
        }
    }

    function productCard(product) {
        const card = cardTemplate.content.cloneNode(true);
        card.querySelector("[data-product-link]").href = product.url;
        card.querySelector("[data-product-name]").textContent = product.name;
        card.querySelector("[data-product-category]").textContent = product.category.name;
        card.querySelector("[data-product-price]").textContent = `Rp${currency.format(product.price)}/${product.unit}`;
        card.querySelector("[data-product-location]").textContent = product.location;
        card.querySelector("[data-product-stock]").textContent = product.is_available ? `Stok: ${product.stock}` : "Habis";
        const image = card.querySelector("[data-product-image]");
        image.hidden = !product.image_url;
        if (product.image_url) image.src = product.image_url;
        image.alt = product.name;
        return card;
    }

    async function showResult(turn, data) {
        const failed = data.status === "failed";
        finishThinking(turn, failed ? [] : interpretation(data.filters || {}, data.degraded), failed);
        const answer = turn.querySelector("[data-answer]");
        if (failed) answer.classList.add("text-danger");
        await streamText(answer, data.explanation || "");
        const products = turn.querySelector("[data-products]");
        for (const product of data.products || []) {
            const card = productCard(product);
            const article = card.firstElementChild;
            if (!reduceMotion) article.classList.add("animate-fade-up");
            products.append(card);
        }
    }

    function showError(turn, message) {
        finishThinking(turn, [], true);
        const answer = turn.querySelector("[data-answer]");
        answer.classList.add("text-danger");
        answer.textContent = message;
    }

    // ---------- Komunikasi dengan server ----------
    async function read(response) {
        if (response.status === 401) throw new Error("Sesi berakhir. Silakan masuk kembali.");
        let body;
        try { body = await response.json(); }
        catch { throw new Error("Respons tidak dapat dibaca. Silakan coba lagi."); }
        if (!response.ok) throw new Error(body.message || "Pencarian belum tersedia. Silakan coba lagi.");
        return body;
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (isSubmitting) return;
        updateWordCount();
        if (!form.reportValidity() || !prompt.value.trim()) return;

        const text = prompt.value.trim();
        const turn = newTurn(text);
        prompt.value = "";
        autoGrow();
        isSubmitting = true;
        updateWordCount();

        try {
            const job = await read(await fetch(form.dataset.createUrl, {
                method: "POST", credentials: "same-origin",
                headers: {"Content-Type": "application/json", "X-CSRFToken": form.elements.csrfmiddlewaretoken.value},
                body: JSON.stringify({prompt: text}),
                signal: AbortSignal.timeout(15000),
            }));
            // Batasi lama menunggu: kalau worker tidak berjalan, job akan tetap "pending".
            const deadline = Date.now() + POLL_DEADLINE_MS;
            while (true) {
                if (Date.now() > deadline) {
                    throw new Error("Pencarian terlalu lama diproses. Coba lagi nanti atau jelajahi marketplace.");
                }
                await sleep(1500);
                const data = await read(await fetch(job.status_url, {
                    credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(15000),
                }));
                if (["succeeded", "needs_clarification", "failed"].includes(data.status)) {
                    await showResult(turn, data);
                    break;
                }
                turn.querySelector("[data-thinking-label]").textContent =
                    data.status === "processing" ? "Mencari produk yang cocok" : "Berpikir";
            }
        } catch (error) {
            showError(turn, error.name === "TimeoutError" ? "Koneksi terlalu lama. Silakan coba lagi." :
                (error instanceof TypeError ? "Koneksi terputus. Silakan coba lagi." : error.message));
        } finally {
            isSubmitting = false;
            updateWordCount();
            prompt.focus();
        }
    });
})();
