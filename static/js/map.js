/*
 * Halaman Peta Kebun (map_module). Tampilan mengikuti draf Figma "peta-kebun-desktop".
 *
 * - Daftar + marker dirender dari JSON; seluruh teks dimasukkan lewat textContent
 *   (bukan innerHTML) sehingga data pengguna tidak bisa menyisipkan HTML/skrip.
 * - Peta gagal dimuat (Leaflet/tile diblokir)? Daftar lokasi tetap berfungsi.
 * - "Dekat saya" hanya meminta izin lokasi saat tombol ditekan. Koordinat (dan
 *   radius) dikirim lewat body POST dan tidak disimpan di mana pun (PRD §5.5, §9).
 * - ?product=<id> menampilkan titik pengambilan produk marketplace (PRD §5.5 butir 5).
 */
(function () {
  'use strict';

  var dataEl = document.getElementById('map-initial');
  var cfgEl = document.getElementById('map-config');
  if (!dataEl || !cfgEl) return;

  var cfg = JSON.parse(cfgEl.textContent);
  var locations = JSON.parse(dataEl.textContent);

  var $ = function (id) { return document.getElementById(id); };
  var listEl = $('location-list');
  var emptyEl = $('empty-state');
  var emptyHint = $('empty-hint');
  var EMPTY_HINT_DEFAULT = emptyHint ? emptyHint.textContent : '';
  var statusEl = $('map-status');
  var countEl = $('result-count');
  var searchInput = $('q');
  var formEl = $('filter-form');
  var nearBtn = $('near-me');
  var nearActive = $('near-active');
  var resetBtn = $('near-reset');
  var radiusSel = $('radius');
  var chipAll = document.querySelector('[data-kind-all]');
  var kindChips = Array.prototype.slice.call(document.querySelectorAll('[data-kind]'));
  var cardTpl = $('tpl-card');
  var popupTpl = $('tpl-popup');
  var pinTpl = $('tpl-pin');
  var SELECTED_CLASS = pinTpl ? pinTpl.dataset.selectedClass : '';
  var pin = cfg.product_pin || null;

  var DEFAULT_CENTER = [-2.5, 118]; // tengah Indonesia
  var DEFAULT_ZOOM = 5;
  // Tile standar OpenStreetMap (tanpa API key). Tampilan gelap sesuai draf Figma dibuat
  // dengan filter CSS pada kelas "map-tiles" (static/css/map.css). Basemap CARTO tidak dipakai:
  // sejak 2026 CARTO mewajibkan API key dan tanpa key mengembalikan tile "API KEY REQUIRED".
  var TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  var TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  var state = {
    origin: null, // {lat, lng} hanya di memori
    kinds: new Set(cfg.active_kinds || []),
    controller: null,
    userMarker: null,
    accuracyCircle: null,
    productMarker: null,
    selectedId: null
  };
  var markers = new Map();

  // ---------------------------------------------------------------- peta
  var map = null;
  var layer = null;
  if (window.L) {
    map = L.map('map', { zoomControl: false }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    L.control.zoom({ position: 'topright', zoomInTitle: 'Perbesar', zoomOutTitle: 'Perkecil' }).addTo(map);
    L.tileLayer(TILE_URL, { maxZoom: 19, attribution: TILE_ATTRIBUTION, className: 'map-tiles' }).addTo(map);
    layer = L.layerGroup().addTo(map);
  } else {
    $('map-fallback').hidden = false;
  }

  // ------------------------------------------------------------- utilitas
  function setStatus(message, isError) {
    statusEl.textContent = message || '';
    statusEl.classList.toggle('text-danger', !!isError);
    statusEl.classList.toggle('text-muted', !isError);
  }

  function safeUrl(url) {
    return typeof url === 'string' && /^(https?:\/\/|\/)/i.test(url) ? url : '';
  }

  function csrfToken() {
    var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  /** Data turunan untuk tampilan (tidak mengubah objek asli). */
  function viewModel(loc) {
    var vm = Object.assign({}, loc);
    vm.card_line = loc.commodities || loc.schedule || '';
    // Tombol utama popup: etalase/produk bila ada, kalau tidak detail lokasi.
    vm.primary_url = loc.store_url || loc.detail_url;
    vm.primary_label = loc.store_url ? 'Lihat produk' : 'Lihat detail';
    vm.secondary_url = loc.store_url ? loc.detail_url : '';
    return vm;
  }

  /** Isi satu cetakan (kartu/popup) dari objek lokasi. */
  function fill(root, loc) {
    root.querySelectorAll('[data-text]').forEach(function (el) {
      var value = loc[el.dataset.text];
      el.textContent = value ? (el.dataset.prefix || '') + value + (el.dataset.suffix || '') : '';
      if (el.hasAttribute('hidden') || !value) el.hidden = !value;
    });
    root.querySelectorAll('[data-badge]').forEach(function (el) {
      el.classList.remove('badge-brand', 'badge-warning');
      el.classList.add(loc.badge_tone === 'warning' ? 'badge-warning' : 'badge-brand');
    });
    root.querySelectorAll('[data-show-if]').forEach(function (el) {
      el.hidden = !loc[el.dataset.showIf];
    });
    root.querySelectorAll('[data-link]').forEach(function (el) {
      var url = safeUrl(loc[el.dataset.link]);
      if (url) { el.href = url; el.hidden = false; } else { el.hidden = true; }
    });
    root.querySelectorAll('[data-img]').forEach(function (el) {
      var url = safeUrl(loc[el.dataset.img]);
      var placeholder = el.parentElement && el.parentElement.querySelector('[data-placeholder]');
      if (url) { el.src = url; el.alt = 'Foto ' + loc.name; el.hidden = false; } else { el.hidden = true; }
      if (placeholder) placeholder.style.display = url ? 'none' : '';
    });
    root.querySelectorAll('[data-login-link]').forEach(function (el) {
      el.href = cfg.login_url;
    });
  }

  function isNarrowScreen() {
    // Di ponsel peta ada di atas daftar: gulir ke peta setelah memilih kartu.
    return !!(window.matchMedia && window.matchMedia('(max-width: 1023px)').matches);
  }

  /** Ikon pin dari template; warna per jenis dibaca dari data-pin-colors. */
  function pinIcon(kind, scale) {
    var wrap = pinTpl.content.firstElementChild.cloneNode(true);
    var colors = document.querySelector('template[data-pin-colors="' + kind + '"]');
    if (colors) {
      wrap.querySelector('[data-pin-body]').setAttribute('class', colors.dataset.body);
      wrap.querySelector('[data-pin-dot]').setAttribute('class', colors.dataset.dot);
    }
    var s = scale || 1;
    var svg = wrap.querySelector('svg');
    svg.setAttribute('width', String(28 * s));
    svg.setAttribute('height', String(36 * s));
    return L.divIcon({
      html: wrap.outerHTML,
      className: '',
      iconSize: [28 * s, 36 * s],
      iconAnchor: [14 * s, 36 * s],
      popupAnchor: [0, -36 * s - 6]
    });
  }

  // ------------------------------------------------------------- render
  function setMarkerSelected(marker, selected) {
    var el = marker && marker.getElement && marker.getElement();
    var pinEl = el && el.querySelector('[data-pin]');
    if (pinEl && SELECTED_CLASS) pinEl.classList.toggle(SELECTED_CLASS, selected);
    if (marker && marker.setZIndexOffset) marker.setZIndexOffset(selected ? 500 : 0);
  }

  function highlight(id) {
    state.selectedId = id;
    listEl.querySelectorAll('[data-card]').forEach(function (card) {
      var selected = Number(card.dataset.id) === id;
      card.classList.toggle('card-selected', selected);
      if (selected) card.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });
    markers.forEach(function (marker, markerId) { setMarkerSelected(marker, markerId === id); });
  }

  function focusLocation(id, scrollToMap) {
    var marker = markers.get(id);
    if (!marker || !map) return;
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15));
    marker.openPopup();
    highlight(id);
    if (scrollToMap) $('map').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function fitMap() {
    if (!map) return;
    var points = locations.map(function (l) { return [l.lat, l.lng]; });
    if (state.origin) points.push([state.origin.lat, state.origin.lng]);
    if (pin) points.push([pin.lat, pin.lng]);
    if (points.length === 0) { map.setView(DEFAULT_CENTER, DEFAULT_ZOOM); return; }
    // Padding bawah lebih besar agar pin tidak tertutup legenda.
    map.fitBounds(L.latLngBounds(points), { paddingTopLeft: [48, 48], paddingBottomRight: [64, 120], maxZoom: 15 });
  }

  function popupOptions() {
    return { maxWidth: 320, minWidth: 288, closeButton: false, autoPanPadding: [24, 24], keepInView: true };
  }

  function render() {
    listEl.replaceChildren();
    markers.clear();
    if (layer) layer.clearLayers();

    locations.forEach(function (loc) {
      var vm = viewModel(loc);
      var card = cardTpl.content.firstElementChild.cloneNode(true);
      card.dataset.id = loc.id;
      fill(card, vm);
      // Seluruh kartu bisa diklik (sesuai desain Figma); tombol nama menjaga akses keyboard.
      card.addEventListener('click', function (event) {
        if (event.target.closest('a')) return;
        if (!map) { // peta tidak termuat: buka halaman detail
          var url = safeUrl(loc.detail_url);
          if (url) window.location.assign(url);
          return;
        }
        focusLocation(loc.id, isNarrowScreen());
      });
      listEl.appendChild(card);

      if (map) {
        var popup = popupTpl.content.firstElementChild.cloneNode(true);
        fill(popup, vm);
        var marker = L.marker([loc.lat, loc.lng], { icon: pinIcon(loc.kind), title: loc.name, alt: loc.name });
        marker.bindPopup(popup, popupOptions());
        marker.on('click', function () { highlight(loc.id); });
        marker.addTo(layer);
        markers.set(loc.id, marker);
      }
    });

    if (state.selectedId !== null && markers.has(state.selectedId)) highlight(state.selectedId);

    emptyEl.hidden = locations.length > 0;
    if (emptyHint) {
      emptyHint.textContent = state.origin && radiusSel && radiusSel.value
        ? 'Tidak ada lokasi dalam radius ' + radiusSel.value + ' km. Coba perbesar radius.'
        : EMPTY_HINT_DEFAULT;
    }
    countEl.textContent = locations.length
      ? locations.length + ' lokasi' + (state.origin ? ' · diurutkan dari yang terdekat' : '')
      : '';
    fitMap();
  }

  // --------------------------------------------------------------- data
  function currentFilters() {
    return { q: searchInput.value.trim(), kinds: Array.from(state.kinds) };
  }

  function syncUrl() {
    // Koordinat pengguna dan radius sengaja TIDAK dimasukkan ke URL.
    var f = currentFilters();
    var params = new URLSearchParams();
    if (pin) params.set('product', String(pin.id));
    if (f.q) params.set('q', f.q);
    f.kinds.forEach(function (k) { params.append('kind', k); });
    var qs = params.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  }

  async function refresh() {
    var f = currentFilters();
    if (state.controller) state.controller.abort();
    state.controller = new AbortController();
    var signal = state.controller.signal;
    setStatus('Memuat lokasi…');

    try {
      var resp;
      if (state.origin) {
        resp = await fetch(cfg.nearby_url, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
          body: JSON.stringify({
            lat: state.origin.lat,
            lng: state.origin.lng,
            q: f.q,
            kind: f.kinds,
            radius_km: radiusSel && radiusSel.value ? Number(radiusSel.value) : null
          }),
          signal: signal
        });
      } else {
        var params = new URLSearchParams();
        if (f.q) params.set('q', f.q);
        f.kinds.forEach(function (k) { params.append('kind', k); });
        resp = await fetch(cfg.api_url + '?' + params.toString(), {
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
          signal: signal
        });
      }
      if (!resp.ok) {
        var err = await resp.json().catch(function () { return {}; });
        throw new Error(err.error || 'Gagal memuat lokasi. Coba lagi.');
      }
      var body = await resp.json();
      locations = body.results;
      render();
      syncUrl();
      setStatus('');
    } catch (e) {
      if (e.name === 'AbortError') return;
      setStatus(e.message || 'Gagal memuat lokasi. Coba lagi.', true);
    }
  }

  // ---------------------------------------------------------- dekat saya
  function clearUserMarker() {
    if (state.userMarker) { state.userMarker.remove(); state.userMarker = null; }
    if (state.accuracyCircle) { state.accuracyCircle.remove(); state.accuracyCircle = null; }
  }

  function showUserMarker(accuracyMeters) {
    if (!map || !state.origin) return;
    clearUserMarker();
    var latlng = [state.origin.lat, state.origin.lng];
    if (accuracyMeters && isFinite(accuracyMeters) && L.circle) {
      state.accuracyCircle = L.circle(latlng, {
        radius: Math.min(accuracyMeters, 2000), className: 'map-accuracy', interactive: false
      }).addTo(map);
    }
    state.userMarker = L.marker(latlng, {
      icon: L.divIcon({ html: $('tpl-user-marker').innerHTML, className: '', iconSize: [16, 16], iconAnchor: [8, 8] }),
      title: 'Posisi Anda',
      alt: 'Posisi Anda',
      interactive: false,
      keyboard: false
    }).addTo(map);
  }

  function setNearUi(active) {
    nearBtn.hidden = active;
    if (nearActive) nearActive.hidden = !active;
  }

  function geoErrorMessage(err) {
    if (err && err.code === 1) return 'Izin lokasi ditolak. Peta dan pencarian manual tetap berfungsi.';
    if (err && err.code === 3) return 'Lokasi Anda terlalu lama ditentukan. Peta dan pencarian manual tetap berfungsi.';
    return 'Lokasi Anda tidak dapat ditentukan. Peta dan pencarian manual tetap berfungsi.';
  }

  if ('geolocation' in navigator) {
    nearBtn.hidden = false;
    nearBtn.addEventListener('click', function () {
      nearBtn.disabled = true;
      setStatus('Meminta izin lokasi…');
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          nearBtn.disabled = false;
          state.origin = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          setNearUi(true);
          showUserMarker(pos.coords.accuracy);
          refresh();
        },
        function (err) {
          nearBtn.disabled = false;
          setStatus(geoErrorMessage(err), true);
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
      );
    });
    resetBtn.addEventListener('click', function () {
      state.origin = null;
      if (radiusSel) radiusSel.value = '';
      clearUserMarker();
      setNearUi(false);
      refresh();
    });
  }

  // ------------------------------------------------------------ interaksi
  document.querySelectorAll('.no-js-only').forEach(function (el) { el.hidden = true; });
  if (radiusSel) radiusSel.addEventListener('change', refresh);

  function syncChips() {
    kindChips.forEach(function (chip) {
      chip.setAttribute('aria-pressed', state.kinds.has(chip.dataset.kind) ? 'true' : 'false');
    });
    if (chipAll) chipAll.setAttribute('aria-pressed', state.kinds.size === 0 ? 'true' : 'false');
  }

  kindChips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var kind = chip.dataset.kind;
      if (state.kinds.has(kind)) state.kinds.delete(kind); else state.kinds.add(kind);
      // Semua jenis terpilih = sama dengan "Semua".
      if (state.kinds.size === kindChips.length) state.kinds.clear();
      syncChips();
      refresh();
    });
  });
  if (chipAll) {
    chipAll.addEventListener('click', function () {
      if (state.kinds.size === 0) return;
      state.kinds.clear();
      syncChips();
      refresh();
    });
  }

  var debounceId = null;
  searchInput.addEventListener('input', function () {
    clearTimeout(debounceId);
    debounceId = setTimeout(refresh, 300);
  });
  formEl.addEventListener('submit', function (event) {
    event.preventDefault();
    refresh();
  });

  // ------------------------------------------------------ pin produk
  /** Marker titik pengambilan produk; dipasang langsung ke peta agar tidak hilang saat daftar disaring. */
  function showProductPin() {
    if (!pin || !map) return;
    var popup = $('tpl-product-popup').content.firstElementChild.cloneNode(true);
    fill(popup, pin);
    state.productMarker = L.marker([pin.lat, pin.lng], {
      icon: pinIcon('product', 1.3),
      title: 'Titik pengambilan: ' + pin.name,
      alt: 'Titik pengambilan: ' + pin.name,
      zIndexOffset: 1000
    }).bindPopup(popup, popupOptions()).addTo(map);
  }

  // --------------------------------------------------------------- mulai
  syncChips();
  showProductPin();
  render();
  if (pin && state.productMarker) {
    map.setView([pin.lat, pin.lng], 16);
    // Buka popup setelah ukuran peta final, supaya autoPan menghitung batas yang benar
    // (sebelumnya popup terpotong di tepi kanan).
    map.whenReady(function () {
      setTimeout(function () {
        map.invalidateSize();
        state.productMarker.openPopup();
      }, 150);
    });
  } else if (pin) {
    // Peta tidak termuat: tetap beri tahu di mana titik pengambilannya.
    setStatus('Titik pengambilan "' + pin.name + '": ' +
      ([pin.address, pin.area].filter(Boolean).join(', ') || 'alamat belum diisi') + '.');
  } else if (cfg.product_missing) {
    setStatus('Titik pengambilan produk ini tidak tersedia. Menampilkan semua lokasi.', true);
  }
  // Pin produk didahulukan; ?focus hanya dipakai bila tidak ada pin produk.
  if (cfg.focus_id && !pin) {
    var exists = locations.some(function (l) { return l.id === cfg.focus_id; });
    if (!exists) {
      setStatus('Lokasi yang dimaksud tidak tersedia atau sudah disembunyikan.', true);
    } else if (map) {
      focusLocation(cfg.focus_id, false);
    } else {
      highlight(cfg.focus_id); // peta tidak termuat: sorot kartunya saja
    }
  }
})();
