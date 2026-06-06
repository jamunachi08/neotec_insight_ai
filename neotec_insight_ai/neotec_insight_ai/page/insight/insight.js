frappe.pages['insight'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Neotec Insight AI',
    single_column: true,
  });

  // Full-bleed iframe keeps the cockpit's styles isolated from Desk while
  // still sharing the same origin, so the app can call frappe.call() on the
  // parent window for live data and the NeoNexus AI bridge.
  const $main = $(wrapper).find('.layout-main-section').css({ padding: 0, border: 0 });
  const frame = document.createElement('iframe');
  frame.id = 'nia-frame';
  frame.src = '/assets/neotec_insight_ai/insight/app.html?v=' + (window.frappe ? frappe.boot.developer_mode || '2' : '2');
  frame.setAttribute('title', 'Neotec Insight AI');
  frame.style.cssText = 'width:100%;border:0;display:block;height:calc(100vh - 110px);background:#f7f7f5;';
  $main.empty().append(frame);

  page.set_primary_action('Settings', () => frappe.set_route('Form', 'Insight Settings'), 'setting');
};
