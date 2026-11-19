(function () {
  var business = {
    productName: 'proNotify',
    legalName: '[Your registered company name]',
    contactName: '[Contact person]',
    address: '[Registered business address, Thailand]',
    phone: '[+66 XX XXX XXXX]',
    email: 'support@pronotify.site',
    website: 'https://pronotify.site',
    hours: 'Monday-Friday, 09:00-18:00 (ICT)',
    taxId: '[Thai tax ID / company registration number]'
  };

  function apply() {
    document.querySelectorAll('[data-biz]').forEach(function (el) {
      var key = el.getAttribute('data-biz');
      if (business[key]) el.textContent = business[key];
    });
    document.querySelectorAll('[data-biz-email]').forEach(function (el) {
      el.setAttribute('href', 'mailto:' + business.email);
      el.textContent = business.email;
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', apply);
  } else {
    apply();
  }
})();
