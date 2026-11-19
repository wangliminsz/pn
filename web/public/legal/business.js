(function () {
  var business = {
    productName: 'proNotify',
    legalName: 'Ant Global Property Co., Ltd.',
    contactName: 'Daisy Chan',
    address: 'Interchange 21 Building, Asoke, Bangkok 10110',
    phone: '+66 0800252616',
    email: 'antglobalproperty3@gmail.com',
    website: 'https://pronotify.site',
    hours: 'Monday-Friday, 09:00-18:00 (ICT)',
    taxId: '0105561199314'
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
