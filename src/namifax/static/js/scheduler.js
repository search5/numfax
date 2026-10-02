/* Scheduled Tasks page: the start/stop box refreshes by itself and a click on Start/Stop changes it at once, without reloading. */
(function () {
  var box = document.getElementById('scheduler-state');
  if (!box || !window.fetch) return;
  var url = box.getAttribute('data-state-url');
  var busy = false;

  function show(html) { box.innerHTML = html; }

  function refresh() {
    if (busy) return;
    fetch(url, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.text() : null; })
      .then(function (html) { if (html && !busy) show(html); }).catch(function () {});
  }

  box.addEventListener('submit', function (event) {
    var form = event.target.closest('form[data-scheduler-action]');
    if (!form) return;
    event.preventDefault();
    busy = true;
    // (form.action would be the <input name="action">, so the attribute is read)
    fetch(form.getAttribute('action'), { method: 'POST', body: new URLSearchParams(new FormData(form)), credentials: 'same-origin',
                         headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.text(); }).then(show).catch(function () { HTMLFormElement.prototype.submit.call(form); })
      .finally(function () { busy = false; });
  });

  setInterval(refresh, 3000);
})();
