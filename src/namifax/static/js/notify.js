/* New-fax notification and modem status, like the original's avantfax.js / ajaxmodemstatus.js:
 * the unread count is fetched every 30 seconds (data-inbox-poll), the modem status every 20 seconds (data-modem-poll).
 * A new fax updates the badge and the title, tries to bring the window forward, shows a browser notification when it was
 * allowed and plays the user's sound file. There is no modal alert. */
(function () {
  var body = document.body;
  if (!body || !window.fetch) return;

  var inboxEvery = parseInt(body.getAttribute('data-inbox-poll') || '30', 10) * 1000;
  var modemEvery = parseInt(body.getAttribute('data-modem-poll') || '20', 10) * 1000;
  var baseTitle = document.title.replace(/^\(\d+\)\s*/, '');
  var current = null;

  function setBadges(count) {
    document.querySelectorAll('[data-inbox-count]').forEach(function (el) { el.textContent = count; });
    document.title = (count > 0 ? '(' + count + ') ' : '') + baseTitle;
  }

  function announce(count, sound) {
    try { window.focus(); } catch (e) {}
    if (window.Notification && Notification.permission === 'granted') {
      try { new Notification('NamiFAX', { body: count + ' ' + (body.getAttribute('data-new-fax') || 'new fax') }); } catch (e) {}
    }
    if (sound) {
      try { new Audio('/audio/' + encodeURIComponent(sound)).play(); } catch (e) {}
    }
  }

  function checkInbox() {
    fetch('/ajax/inbox?randid=' + Math.random(), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.text() : ''; })
      .then(function (text) {
        var parts = text.trim().split('|');
        var count = parseInt(parts[0], 10);
        if (isNaN(count)) return;
        if (current !== null && count > current) announce(count, parts[1]);
        current = count;
        setBadges(count);
      })
      .catch(function () {});
  }

  function checkModems() {
    var holder = document.querySelector('[data-modems]');
    if (!holder) return;
    var devices = (holder.getAttribute('data-modems') || '').split(',').filter(Boolean);
    if (!devices.length) return;
    fetch('/ajax/modemstatus?randid=' + Math.random() + '&modems=' + encodeURIComponent(devices.join(',')), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.text() : ''; })
      .then(function (text) {
        var rows = new DOMParser().parseFromString(text, 'text/xml').getElementsByTagName('row');
        var summary = [];
        for (var i = 0; i < rows.length; i++) {
          var device = rows[i].getElementsByTagName('modem')[0].textContent;
          var status = rows[i].getElementsByTagName('status')[0].textContent;
          var css = rows[i].getElementsByTagName('class')[0].textContent;
          document.querySelectorAll('[data-modem="' + device + '"]').forEach(function (el) {
            el.textContent = status;
            el.className = el.className.replace(/\bmodem-\w+\b/g, '') + ' ' + css;
          });
          summary.push(status);
        }
        var line = holder.querySelector('[data-modem-summary]');
        if (line && summary.length) line.textContent = summary.length === 1 ? summary[0] : summary.length + ' ' + (holder.getAttribute('data-lines') || 'lines');
      })
      .catch(function () {});
  }

  var badge = document.querySelector('[data-inbox-count]');
  current = badge ? parseInt(badge.textContent, 10) || 0 : 0;
  setBadges(current);
  setInterval(checkInbox, inboxEvery);
  setInterval(checkModems, modemEvery);
  if (window.Notification && Notification.permission === 'default') {
    document.addEventListener('click', function ask() {
      document.removeEventListener('click', ask);
      try { Notification.requestPermission(); } catch (e) {}
    });
  }
})();
