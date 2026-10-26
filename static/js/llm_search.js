(() => {
    "use strict";
    const form = document.getElementById("llm-search-form");
    if (!form) return;
    const status = document.getElementById("search-status");
    const button = form.querySelector("button[type=submit]");
    const result = document.getElementById("search-result");
    const products = document.getElementById("search-products");
    const currency = new Intl.NumberFormat("id-ID");
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

    function render(data) {
        result.hidden = false;
        document.getElementById("search-explanation").textContent = data.explanation || "";
        const filters = data.filters || {};
        const labels = [];
        if (filters.keyword) labels.push(`Produk: ${filters.keyword}`);
        if (filters.categories?.length) labels.push(`Kategori: ${filters.categories.join(", ")}`);
        if (filters.location) labels.push(`Lokasi: ${filters.location}`);
        if (filters.min_price != null) labels.push(`Minimum Rp${currency.format(filters.min_price)}`);
        if (filters.max_price != null) labels.push(`Maksimum Rp${currency.format(filters.max_price)}`);
        if (filters.in_stock) labels.push("Stok tersedia");
        document.getElementById("search-filters").textContent = labels.join(" · ");
        products.replaceChildren();
        for (const product of data.products || []) {
            const card = document.getElementById("product-card-template").content.cloneNode(true);
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
            products.append(card);
        }
    }

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
        if (button.disabled) return;
        button.disabled = true;
        result.hidden = true;
        status.textContent = "Menunggu pencarian diproses…";
        try {
            const job = await read(await fetch(form.dataset.createUrl, {
                method: "POST", credentials: "same-origin",
                headers: {"Content-Type": "application/json", "X-CSRFToken": form.elements.csrfmiddlewaretoken.value},
                body: JSON.stringify({prompt: form.elements.prompt.value}),
                signal: AbortSignal.timeout(15000),
            }));
            while (true) {
                await sleep(2000);
                const data = await read(await fetch(job.status_url, {
                    credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(15000),
                }));
                if (["succeeded", "needs_clarification", "failed"].includes(data.status)) {
                    render(data);
                    status.textContent = data.status === "failed" ? "Pencarian belum berhasil." : "Pencarian selesai.";
                    break;
                }
                status.textContent = data.status === "processing" ? "Sedang mencari produk yang sesuai…" : "Menunggu pencarian diproses…";
            }
        } catch (error) {
            status.textContent = error.name === "TimeoutError" ? "Koneksi terlalu lama. Silakan coba lagi." :
                (error instanceof TypeError ? "Koneksi terputus. Silakan coba lagi." : error.message);
        } finally { button.disabled = false; }
    });
})();
