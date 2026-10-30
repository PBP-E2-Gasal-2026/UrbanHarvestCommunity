/*
 * Peta satu titik (halaman detail lokasi & form tambah/ubah).
 *
 * Mode baca : tampilkan marker di koordinat lokasi.
 * Mode edit : klik peta atau isi kolom latitude/longitude; keduanya saling sinkron.
 *             Tombol "Gunakan lokasi saya" meminta izin lokasi hanya saat ditekan.
 */
(function () {
  'use strict';

  var el = document.getElementById('point-map');
  if (!el) return;

  var fallback = document.getElementById('point-map-fallback');
  if (!window.L) {
    if (fallback) fallback.hidden = false;
    return;
  }

  var editable = el.dataset.editable === 'true';
  var latInput = document.getElementById(el.dataset.latInput || '');
  var lngInput = document.getElementById(el.dataset.lngInput || '');

  function validPoint(lat, lng) {
    return isFinite(lat) && isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 &&
      !(lat === 0 && lng === 0);
  }

  var lat = parseFloat(el.dataset.lat);
  var lng = parseFloat(el.dataset.lng);
  if (editable && latInput && lngInput && !validPoint(lat, lng)) {
    lat = parseFloat(latInput.value);
    lng = parseFloat(lngInput.value);
  }
  var hasPoint = validPoint(lat, lng);

  var map = L.map(el, { zoomControl: false }).setView(hasPoint ? [lat, lng] : [-2.5, 118], hasPoint ? 16 : 5);
  // Sama dengan map.js: tile OpenStreetMap tanpa API key, digelapkan lewat kelas "map-tiles".
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    className: 'map-tiles',
    // Send only the site origin to OSM, even with Django's same-origin policy.
    referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  L.control.zoom({ position: 'topright', zoomInTitle: 'Perbesar', zoomOutTitle: 'Perkecil' }).addTo(map);

  var markerTpl = document.getElementById('tpl-point-marker');
  var icon = L.divIcon({
    html: markerTpl ? markerTpl.innerHTML : '',
    className: '',
    iconSize: [28, 36],
    iconAnchor: [14, 36]
  });
  var marker = null;

  function placeMarker(la, ln) {
    if (marker) {
      marker.setLatLng([la, ln]);
    } else {
      marker = L.marker([la, ln], { icon: icon, title: el.dataset.name || 'Lokasi', alt: el.dataset.name || 'Lokasi' }).addTo(map);
    }
  }

  if (hasPoint) placeMarker(lat, lng);
  if (!editable) return;

  // ----- mode edit -----
  function writeInputs(la, ln) {
    latInput.value = la.toFixed(6);
    lngInput.value = ln.toFixed(6);
    latInput.dispatchEvent(new Event('change', { bubbles: true }));
  }

  map.on('click', function (event) {
    placeMarker(event.latlng.lat, event.latlng.lng);
    writeInputs(event.latlng.lat, event.latlng.lng);
  });

  function syncFromInputs() {
    var la = parseFloat(latInput.value);
    var ln = parseFloat(lngInput.value);
    if (validPoint(la, ln)) {
      placeMarker(la, ln);
      map.setView([la, ln], Math.max(map.getZoom(), 15));
    }
  }
  latInput.addEventListener('change', syncFromInputs);
  lngInput.addEventListener('change', syncFromInputs);

  var locateBtn = document.getElementById('use-my-location');
  var statusEl = document.getElementById('point-status');
  if (locateBtn && 'geolocation' in navigator) {
    locateBtn.hidden = false;
    locateBtn.addEventListener('click', function () {
      locateBtn.disabled = true;
      if (statusEl) statusEl.textContent = 'Meminta izin lokasi…';
      navigator.geolocation.getCurrentPosition(
        function (pos) {
          locateBtn.disabled = false;
          if (statusEl) statusEl.textContent = '';
          placeMarker(pos.coords.latitude, pos.coords.longitude);
          writeInputs(pos.coords.latitude, pos.coords.longitude);
          map.setView([pos.coords.latitude, pos.coords.longitude], 16);
        },
        function () {
          locateBtn.disabled = false;
          if (statusEl) statusEl.textContent = 'Lokasi tidak tersedia. Klik peta atau isi koordinat secara manual.';
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  }
})();
